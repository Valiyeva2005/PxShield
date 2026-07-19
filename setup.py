"""Setup script for PixelShield."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="pixelshield",
    version="1.0.0",
    author="PixelShield Team",
    description="Advanced Image Encryption CLI Tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pixelshield",
    packages=find_packages(),
    python_requires=">=3.12",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "pixelshield=cli.app:app",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Topic :: Security :: Cryptography",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.12",
        "Operating System :: POSIX :: Linux",
    ],
    package_data={
        "": ["config.yaml"],
    },
)
