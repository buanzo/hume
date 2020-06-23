# -*- coding: utf-8 -*-
from setuptools import setup

# Imports content of requirements.txt into setuptools' install_requires
with open('requirements.txt') as f:
      requirements = f.read().splitlines()

def get_version():
    with open('hume.py') as f:
        for line in f:
            if line.startswith('__version__'):
                return eval(line.split('=')[-1])

# Imports content of README.md into setuptools' long_description
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.txt'), encoding='utf-8') as f:
      long_description = f.read()


setup(name='humed',
      version=get_version(),
      description="Agnostic sysadmin/devops instrumentation tool. Includes hume and humed.",
      long_description=long_description,
      keywords='hume, humed, logstash, slack, syslog, kant, fluentd, devops, sysadmin, agnostic',
      author='Arturo "Buanzo" Busleiman',
      author_email='buanzo@buanzo.com.ar',
      url='https://github.com/buanzo/hume',
      license='MIT License',
      zip_safe=False,
      python_requires='>=3.6',
      py_modules=['hume','humed', 'humetools', 'humeconfig'],
      namespace_packages=[],
      include_package_data=True,
      install_requires=requirements,
      entry_points={
         'console_scripts': [
            'hume = hume:run',
            'humed = humed:main',
            'humeconfig = humeconfig:run',
         ],
      },
      classifiers=[
         'Environment :: Console',
         'Intended Audience :: Developers',
         'License :: OSI Approved :: MIT License',
         'Programming Language :: Python',
         'Programming Language :: Python :: 3.6',
         'Programming Language :: Python :: 3.7',
         'Programming Language :: Python :: 3.8',
         'Programming Language :: Python :: Implementation :: PyPy',
      ],
)
