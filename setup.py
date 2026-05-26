from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bumblebee-cli",
    version="2.1.2",
    description="Dependency security scanner for macOS — detects malicious, vulnerable, and suspicious packages across npm, PyPI, Go, Ruby and more",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Chandu Chitikam",
    author_email="",
    url="https://github.com/Chandu00756/Bumblebee_CLI",
    license="MIT",
    packages=find_packages(),
    install_requires=[
        "rich>=13.7.0",
        "typer>=0.12.0",
        "fpdf2>=2.7.9",
        "questionary>=2.0.1",
        "python-dateutil>=2.9.0",
        "requests>=2.31.0",
        "packaging>=24.0",
    ],
    entry_points={"console_scripts": ["bee=bbcli.main:app"]},
    python_requires=">=3.11",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Environment :: Console",
        "Topic :: Security",
        "Topic :: Software Development :: Quality Assurance",
    ],
    keywords=["security", "supply-chain", "scanner", "bumblebee", "cli", "sbom"],
    project_urls={
        "Bug Tracker": "https://github.com/Chandu00756/Bumblebee_CLI/issues",
        "Source": "https://github.com/Chandu00756/Bumblebee_CLI",
    },
)