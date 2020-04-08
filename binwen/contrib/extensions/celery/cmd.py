import sys

from celery.__main__ import main as celerymain

from binwen.cli import cli


@cli.command('celery', help='invoke celery commands')
def main(argv):
    sys.argv = ['celery'] + argv + \
        ['-A', 'extensions:celeryapp']
    return celerymain()
