from setuptools import setup

setup(
    name='niceday_client',
    version='0.1',
    author='Robin Richardson, Sven van den Burg, Bouke Scheltinga, Nele Albers',
    install_requires=open("requirements.txt", "r").readlines(),
    long_description=open("README.md", "r").read(),
    long_description_content_type='text/markdown',
    packages=['niceday_client'],
    include_package_data=True,
    description="Python package for interacting with the niceday-api component of the PerfectFit virtual coach",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
    ],
)
