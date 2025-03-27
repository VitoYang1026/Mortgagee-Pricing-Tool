from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mortgage_pricing_tool",
    version="1.0.0",
    author="Mortgage Pricing Team",
    author_email="example@example.com",
    description="A tool for comparing mortgage pricing between AAA and investor ratesheets",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/mortgage_pricing_tool",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "mortgage-pricing-tool=mortgage_pricing_tool.app:main",
        ],
    },
)
