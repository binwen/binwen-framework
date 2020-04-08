from binwen.cli import cli, CommandException
from binwen import current_app


@cli.command('config_hello')
@cli.option('-n', '--name', default='ATTR')
def f1(name, **kwargs):
    raise CommandException(name)


@cli.command('plusone')
@cli.option('-n', '--number', type=int)
def f2(number, **kwargs):
    app = current_app
    app.config['NUMBER'] = number + 1
