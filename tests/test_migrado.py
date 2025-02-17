from pathlib import Path

import pytest

from migrado import migrado
from migrado.constants import MIGRATION_TEMPLATE
from .test_db import (
    MigrationClient,
    TLS, HOST, PORT, USERNAME, PASSWORD, DB, COLL
)


def test_migrado(runner):
    result = runner.invoke(migrado)
    assert result.exit_code == 0


def test_migrado_init(runner, clean_arango):
    with runner.isolated_filesystem():

        result = runner.invoke(migrado, ['init'])
        assert result.exit_code == 0
        assert 'Initial migration written' in result.output
        assert Path('migrations').exists()
        assert Path('migrations/0001_initial.js').exists()

        result = runner.invoke(migrado, ['init'])
        assert result.exit_code == 0
        assert 'Initial migration already exists' in result.output

        result = runner.invoke(migrado, ['init', '--path', 'migrados'])
        assert result.exit_code == 0
        assert 'Initial migration written' in result.output
        assert Path('migrados').exists()
        assert Path('migrados/0001_initial.js').exists()


def test_migrado_init_schema(runner, clean_arango):
    schema_path = Path('tests/test_schema.yml').resolve()
    with runner.isolated_filesystem():

        result = runner.invoke(migrado, ['init', '--schema', schema_path])
        assert result.exit_code == 0
        assert Path('migrations').exists()
        assert Path('migrations/0001_initial.js').exists()

        with Path('migrations/0001_initial.js').open('r') as f:
            content = f.read()
            assert 'db._create("books", {})' in content
            assert 'db._create("authors", {})' in content
            assert 'db._create("author_of", {}, "edge")' in content
            assert content.index('db._create("author_of",') > content.index('forward()')
            assert content.index('db._create("author_of",') < content.index('reverse()')

            assert 'db._drop("books")' in content
            assert 'db._drop("authors")' in content
            assert 'db._drop("author_of")' in content
            assert content.index('db._drop("author_of")') > content.index('reverse()')
            assert content.index('db._drop("author_of")') < content.index('forward() // default')


def test_migrado_init_schema_validation(runner, clean_arango):
    schema_path = Path('tests/test_schema.yml').resolve()
    with runner.isolated_filesystem():

        result = runner.invoke(migrado, ['init', '--schema', schema_path, '--validation=moderate'])
        assert result.exit_code == 0
        assert Path('migrations').exists()
        assert Path('migrations/0001_initial.js').exists()

        with Path('migrations/0001_initial.js').open('r') as f:
            content = f.read()
            assert 'db._create("books", {"schema": {' in content
            assert 'db._create("authors", {})' in content
            assert 'db._create("author_of", {"schema": {' in content


def test_migrado_init_infer(runner, clean_arango):
    schema_path = Path('tests/test_schema.yml').resolve()
    with runner.isolated_filesystem():
        result = runner.invoke(migrado, ['init', '--schema', schema_path])
        result = runner.invoke(migrado, ['run', '--no-interaction'])

    with runner.isolated_filesystem():

        result = runner.invoke(migrado, ['init', '--infer'])
        assert result.exit_code == 0
        assert 'State is now at 0001.' in result.output
        assert Path('migrations').exists()
        assert Path('migrations/0001_initial.js').exists()

        with Path('migrations/0001_initial.js').open('r') as f:
            content = f.read()
            assert 'db._create("books", {})' in content
            assert 'db._create("authors", {})' in content
            assert 'db._create("author_of", {}, "edge")' in content


def test_migrado_inspect(runner, clean_arango):
    with runner.isolated_filesystem():

        result = runner.invoke(migrado, ['init'])
        assert result.exit_code == 0

        result = runner.invoke(migrado, ['inspect'])
        assert result.exit_code == 0
        assert 'Database migration state is at 0000' in result.output
        assert 'Latest migration on disk is 0001' in result.output


def test_migrado_export(runner, clean_arango):
    schema_path = Path('tests/test_schema.yml').resolve()
    with runner.isolated_filesystem():

        result = runner.invoke(migrado, ['export'])
        assert result.exit_code == 0
        assert 'collections:' in result.output
        assert '  books:' not in result.output
        assert 'edge_collections:' in result.output

        result = runner.invoke(migrado, ['init', '--schema', schema_path])
        assert result.exit_code == 0

        result = runner.invoke(migrado, ['run', '--no-interaction'])
        assert result.exit_code == 0

        result = runner.invoke(migrado, ['export'])
        assert result.exit_code == 0
        assert 'collections:' in result.output
        assert '  books:' in result.output
        assert '  authors:' in result.output
        assert 'edge_collections:' in result.output
        assert '  author_of:' in result.output

        result = runner.invoke(migrado, ['export', 'test.yml'])
        assert result.exit_code == 0

        with Path('test.yml').open('r') as f:
            content = f.read()
            assert 'collections:' in content
            assert '  books:' in content
            assert '  authors:' in content
            assert 'edge_collections:' in content
            assert '  author_of:' in content


def test_migrado_make(runner, clean_arango):
    with runner.isolated_filesystem():

        result = runner.invoke(migrado, ['init'])
        assert result.exit_code == 0

        result = runner.invoke(migrado, ['make'])
        assert result.exit_code == 0
        assert 'New migration template written' in result.output
        assert Path('migrations/0002.js').exists()

        result = runner.invoke(migrado, ['make', '--name', 'test'])
        assert result.exit_code == 0
        assert 'New migration template written' in result.output
        assert Path('migrations/0003_test.js').exists()

        with Path('migrations/0003_test.js').open('r') as f:
            content = f.read()
            assert MIGRATION_TEMPLATE in content

    schema_path = Path('tests/test_schema.yml').resolve()
    new_schema_path = Path('tests/test_schema_updated.yml').resolve()
    with runner.isolated_filesystem():

        result = runner.invoke(migrado, ['init', '--schema', schema_path, '--validation=moderate'])
        assert result.exit_code == 0

        result = runner.invoke(migrado, ['run', '--no-interaction'])
        assert result.exit_code == 0

    client = MigrationClient(TLS, HOST, PORT, USERNAME, PASSWORD, DB, COLL)
    client.state_coll.truncate()
    with runner.isolated_filesystem():

        result = runner.invoke(migrado, ['init'])
        assert result.exit_code == 0

        result = runner.invoke(migrado, ['make', '--schema', new_schema_path, '--validation=moderate', '--no-interaction'])
        assert result.exit_code == 0

        result = runner.invoke(migrado, ['run', '--no-interaction'])
        assert result.exit_code == 0

        result = runner.invoke(migrado, ['make', '--schema', schema_path, '--validation=moderate', '--no-interaction'])
        assert result.exit_code == 0


def test_migrado_run(runner, clean_arango):
    schema_path = Path('tests/test_schema.yml').resolve()
    with runner.isolated_filesystem():

        result = runner.invoke(migrado, ['init', '--schema', schema_path, '--validation=moderate'])
        assert result.exit_code == 0

        result = runner.invoke(migrado, ['run', '--target', '0002'])
        assert result.exit_code == 2
        assert 'Target 0002 not found' in result.output

        result = runner.invoke(migrado, ['run', '--db', ''])
        assert result.exit_code == 2
        assert 'Database name not specified' in result.output

        result = runner.invoke(migrado, ['run', '--host', 'nohost'])
        assert result.exit_code == 1
        assert 'Name or service not known' in result.output

        result = runner.invoke(migrado, ['run', '--arangosh', '/bad/path'])
        assert result.exit_code == 1
        assert 'No such file or directory' in result.output

        result = runner.invoke(migrado, ['run', '--no-interaction'])
        assert result.exit_code == 0
        assert 'State is now at 0001.' in result.output
        assert 'Done.' in result.output
