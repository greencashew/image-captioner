from setuptools import setup, find_packages

setup(
    name='icaptioner',
    version=1.0,
    url="https://github.com/greencashew/image-captioner",
    author="Jan Górkiewicz (https://greencashew.dev/)",
    license='MIT',
    description='Command line python script for adding captions to the images based on the metadata or user input',

    packages=find_packages(),
    package_data={'imagecaptioner': ['fonts/*.ttf']},
    install_requires=['Pillow'],
    entry_points={'console_scripts': ['icaptioner = imagecaptioner.main:main']}
)
