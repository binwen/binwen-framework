import sys
import os
import argparse
import pkg_resources
import logging

from binwen.utils.functional import import_obj
from binwen import current_app, create_app

logger = logging.getLogger('binwen.cmd')


class CommandException(RuntimeError):
    pass


class CommandOption:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class CommandManager:

    def __init__(self):
        self._commands = {}

    def command(self, name, env='dev', app=True, *args, **kwargs):

        def wrapper(func):
            if name in self._commands:
                raise CommandException(f"Error: The command name `{name}` already exists. module: {func.__module__}")
            func.parser = CommandOption(*args, **kwargs)
            func.app = app
            func.env = env
            self._commands[name] = func
            return func
        return wrapper

    @staticmethod
    def option(*args, **kwargs):
        def wrapper(func):
            opts = getattr(func, 'opts', [])
            opts.append(CommandOption(*args, **kwargs))
            func.opts = opts
            return func
        return wrapper

    @property
    def commands(self):
        return self._commands


cli = CommandManager()


def _load_commands():
    path = os.getcwd()
    sys.path.append(path)

    import_obj('binwen.commands')

    for ep in pkg_resources.iter_entry_points('binwen.clis'):
        try:
            ep.load()
        except Exception as e:
            logger.debug(f'error has occurred during pkg loading: {e}')

    if not current_app:
        create_app()

    for app in current_app.config["INSTALLED_APPS"]:
        try:
            import_obj(f"{app}.commands")
        except ImportError as e:
            pass


def _build_parser(subparsers):
    for name, handler in cli.commands.items():
        parser = handler.parser
        opts = getattr(handler, 'opts', [])
        p = subparsers.add_parser(name, *parser.args, **parser.kwargs)
        for opt in opts:
            p.add_argument(*opt.args, **opt.kwargs)

        p.set_defaults(handler=handler)


def _run(root):
    args = sys.argv[1:] or ['--help']
    known, argv = root.parse_known_args(args)
    kwargs = vars(known)
    handler = kwargs.pop('handler')
    os.environ.setdefault('BINWEN_ENV', handler.env)
    if handler.app:
        create_app()

    try:
        return handler(**kwargs, argv=argv)
    except CommandException as e:
        return e


def main(raise_exception=True):
    root = argparse.ArgumentParser('bw')
    subparsers = root.add_subparsers()
    try:
        _load_commands()
    except CommandException as e:
        if raise_exception:
            return e
        else:
            print(e)

    _build_parser(subparsers)

    return _run(root)
