from setuptools import setup, find_packages

try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    try:
        with open("readme.md", "r", encoding="utf-8") as fh:
            long_description = fh.read()
    except FileNotFoundError:
        long_description = "A web application for VM provisioning using VMware"

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip() for line in fh if line.strip() and not line.startswith("#")
    ]

setup(
    name="vm_provisioning_app",
    version="1.0.0",
    author="Your Name",
    description="A web application for VM provisioning using VMware",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "vm-provisioning=app:app.run",
        ],
    },
    package_data={
        "": ["templates/*.html"],
    },
)
