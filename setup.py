from setuptools import setup, find_packages

setup(
    name="PgDbToolkit",
    version="0.1.2",
    author="Gustavo Inostroza",
    author_email="gusinostrozar@gmail.com",
    description="A package for managing PostgreSQL database operations",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Inostroza7/PgDbToolkit",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.2.2",
        "psycopg[binary]>=3.2.1",
        "python-dotenv>=1.0.1"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)