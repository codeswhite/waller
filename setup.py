import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

project_name = "waller"

setuptools.setup(
    name=project_name,
    version="0.3.4",
    description="Python curses utility to cycle between desktop wallpapers",
    url=f"https://github.com/codeswhite/{project_name}",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Unix",
    ],
    keywords='',
    python_requires='>=3.6',
    install_requires=[],
    entry_points={
        'console_scripts': [
            'waller=waller:main',
        ],
    },
    author="Max G",
    author_email="max3227@gmail.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages()
)
