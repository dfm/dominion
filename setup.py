import os
from setuptools import find_packages, setup
from pathlib import Path

CURRENT_DIR = Path(__file__).parent


def get_long_description() -> str:
    readme_md = CURRENT_DIR / "README.md"
    with open(readme_md, encoding="utf8") as ld_file:
        return ld_file.read()


setup(
    name="dominion",
    use_scm_version={
        "write_to": os.path.join("src", "dominion", "dominion_version.py"),
        "write_to_template": '__version__ = "{version}"\n',
    },
    description="Generate kingdom sets for the card game Dominion",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Dan Foreman-Mackey",
    author_email="foreman.mackey@gmail.com",
    url="https://github.com/dfm/dominion",
    license="MIT",
    packages=find_packages(where="src"),
    python_requires=">=3.6",
    package_data={"dominion": ["data/cards.json"]},
    include_package_data=True,
    package_dir={"": "src"},
    zip_safe=False,
    install_requires=["click"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
    ],
    entry_points={"console_scripts": ["dominion=dominion:cli"]},
    options={"bdist_wheel": {"universal": "1"}},
)
