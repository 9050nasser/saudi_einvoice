from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in saudi_einvoice/__init__.py
from saudi_einvoice import __version__ as version

setup(
	name="saudi_einvoice",
	version=version,
	description="An app for e-invoicing in Saudi Arabia",
	author="ukkera",
	author_email="gouda@ukkera.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
