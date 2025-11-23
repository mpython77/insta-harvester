"""
InstaHarvest - Professional Instagram Data Collection Toolkit
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="instaharvest",
    version="2.5.3",
    author="Doston",
    author_email="kelajak054@gmail.com",
    description="Professional Instagram data collection toolkit with automation features",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mpython77/insta-harvester",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "playwright>=1.40.0",
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
    # CLI not implemented yet - removed to prevent installation errors
    # entry_points={
    #     "console_scripts": [
    #         "instaharvest=instaharvest.cli:main",
    #     ],
    # },
    keywords=[
        "instagram",
        "scraper",
        "automation",
        "data-collection",
        "social-media",
        "instagram-api",
        "instagram-bot",
        "followers",
        "instagram-scraper",
        "web-scraping",
        "playwright",
    ],
    project_urls={
        "Bug Reports": "https://github.com/mpython77/insta-harvester/issues",
        "Source": "https://github.com/mpython77/insta-harvester",
        "Documentation": "https://github.com/mpython77/insta-harvester#readme",
    },
    include_package_data=True,
    zip_safe=False,
)
