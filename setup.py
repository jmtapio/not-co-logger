#!/usr/bin/env python3

from setuptools import setup


setup(
    name='notcologger',
    version='0.1.2',
    description='Not CO Logger, a cloud logging library.',
    long_description=
'''This library is aimed at helping produce consistent searchable log 
entries to stdout in a cloud/container environment.''',
    keywords='logging',
    url='https://github.com/jmtapio/not-co-logger',
    author='Juha-Matti Tapio',
    author_email='jmtapio@verkkotelakka.net',
    license='MIT',
    packages=['notcologger'],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Logging',
    ],
    python_requires='>=3',
    test_suite='tests.test_logger',
    include_package_data=True,
    zip_safe=True)
