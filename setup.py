from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='tracklater',
    version='1.2',
    description=('TrackLater helps you track time after-the-fact by combining clues and showing'
                 'your day on a simple timeline view.'),
    long_description=long_description,
    long_description_content_type="text/markdown",
    author='Eero Vilpponen',
    author_email='eero.vilpponen@gmail.com',
    packages=find_packages(),
    py_modules=['tracklater'],
    install_requires=requirements,
    python_requires='>=3.7.1',
    include_package_data=True,
    entry_points={
        'console_scripts': ['tracklater = tracklater.__init__:run']
    },
    url="https://github.com/Eerovil/TrackLater",
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
