from setuptools import setup, find_packages

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
    name='imagecaptioner',
    version=0.3,
    url="https://github.com/greencashew/image-captioner",
    author="Jan Górkiewicz (https://greencashew.dev/)",
    license='MIT',
    description='Command line python script for adding captions to the images based on the metadata, filename or user input',
    long_description=long_description,
    long_description_content_type='text/markdown',

    packages=find_packages(),
    package_data={'imagecaptioner': ['fonts/*.ttf']},
    install_requires=['Pillow', 'datefinder'],
    entry_points={'console_scripts': ['imagecaptioner = imagecaptioner.cli:main']}
)
