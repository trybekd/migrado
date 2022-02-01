import setuptools

setuptools.setup(
    name="migrado",
    version="0.6.1",
    description="ArangoDB migrations and batch processing manager",
    url="https://github.com/pypa/sampleproject",
    license="MIT",
    packages=['migrado'],
    python_requires=">=3.6",
    install_requires=[
        'click~=7.1',
        'python-arango~=7.1',
        'pyyaml~=5.4'
    ],
    entry_points={
        'console_scripts': ['migrado=migrado:migrado']
    }
)
