from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='tracklater',
    version='1.1',
    description=('TrackLater helps you track time after-the-fact by combining clues and showing'
                 'your day on a simple timeline view.'),
    author='Eero Vilpponen',
    author_email='eero.vilpponen@gmail.com',
    packages=find_packages(),
    py_modules=['tracklater'],
    install_requires=requirements,
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
