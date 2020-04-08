import os
import re
import ast
from setuptools import setup, find_packages


_version_re = re.compile(r'__version__\s+=\s+(.*)')
_root = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(_root, 'binwen/__version__.py')) as f:
    version = str(ast.literal_eval(_version_re.search(f.read()).group(1)))

with open(os.path.join(_root, 'requirements.txt')) as f:
    requirements = f.readlines()

with open(os.path.join(_root, 'README.md')) as f:
    readme = f.read()


def find_package_data(package):
    walk = [(dirpath.replace(package + os.sep, '', 1), filenames)
            for dirpath, dirnames, filenames in os.walk(package)]

    filepaths = []
    for base, filenames in walk:
        filepaths.extend([os.path.join(base, filename) for filename in filenames])

    return filepaths


setup(
    name='binwen-framework',
    version=version,
    description='grpc framework',
    long_description=readme,
    url='https://github.com/binwen/binwen-framework',
    author='caowenbin',
    author_email='cwb201314@qq.com',
    license='MIT',
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: POSIX',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    keywords=['rpc', 'grpc', 'python3', 'grpc-framework'],
    packages=find_packages(exclude=['tests']),
    package_data={'binwen': find_package_data('binwen')},
    python_requires='>=3',
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'bw=binwen.cli:main'
        ],
        'binwen.clis': [
            'celery=binwen.contrib.extensions.celery.cmd:main',
        ]
    }
)
