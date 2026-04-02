# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

url = "https://repos.digie35.com/python"
setup(
    name='pi_testbench',
    version='0.0.1',
    description='Test platform based on RPI for testing assembled PCBs',
    long_description=readme,
    author='Tomas Mandys',
    author_email='tma@2p.cz',
    url='https://github.com/tmandys/pi-testbench-python.git',
    license=license,
    packages=find_packages(
        where=".",
        exclude=('tests', 'docs'),
    ),
    project_urls={
        "changelog": url+"/CHANGELOG.md",

    },
    #include_package_data=True,
    package_data={
        "pi_testbench": [
            #"html/*.html",
            #"html/*.css",
            #"html/*.js",
            #"html/images/*",
            #"html/audio/*",
            #"systemd/*.service",
            #"desktop/*",
            #"images/*",
            #"nginx/*",
            #"file_template/*"
        ],
    },
    entry_points={
        "console_scripts": [
            "tbench_memory_tool = pi_testbench.memory_tool:main",
        ],
    },
    install_requires = [
        "pyyaml",
        "RPi.GPIO",
        "smbus",
        "smbus2",
        "netifaces",
        "rpi_hardware_pwm",
        "websockets",
        "gpiozero",
        "evdev",
        "lxml",
    ],
    scripts = [
        # "digie35/digie35_lxde-pi-shutdown-helper",
    ],
)

