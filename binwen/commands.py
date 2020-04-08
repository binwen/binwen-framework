import os

from binwen.cli import cli, CommandException
from binwen import current_app
from binwen.server import Server


@cli.command('run', help='Run Server')
@cli.option('addrport', nargs='?', help='Optional port number, or ipaddr:port')
@cli.option("-w", "--workers", default=3, type=int, help='Number of maximum worker threads')
def run_server(addrport, workers, **extra):
    if addrport:
        if ":" not in addrport:
            addrport = f"[::]:{addrport}"
    else:
        addrport = "[::]:50051"

    s = Server(app=current_app, addrport=addrport, workers=workers)
    s.run()
    return 0


@cli.command('shell', help='Runs a shell in the app context')
def shell(**extra):
    banner = """
        [BinWen Shell]:
        the following vars are included:
        `app` (the current app)
        """
    ctx = {'app': current_app}
    try:
        from IPython import embed
        h, kwargs = embed, dict(banner1=banner, user_ns=ctx)
    except ImportError:
        import code
        h, kwargs = code.interact, dict(banner=banner, local=ctx)

    h(**kwargs)

    return 0


@cli.command('make', app=True, help='Make GRPC')
@cli.option('app_proto', nargs='*', help="Specify the app proto(s) to create grpc for.")
def generate(app_proto, **extra):
    app_protos = set(app_proto)
    if not app_protos:
        app_protos = set(current_app.config["INSTALLED_APPS"])

    cwd = os.getcwd()
    finisheds = []
    for app_proto in app_protos:
        path = os.path.join(cwd, app_proto)
        path = path.replace(".", "/")

        for dirpath, dirnames, filenames in os.walk(path):
            rel_path = os.path.relpath(dirpath, cwd)
            protos = [f"./{rel_path}/{fn}" for fn in filenames if fn.endswith(".proto")]
            if not protos:
                continue
            finisheds.extend(protos)
            cmd = [
                'python -m',
                'grpc_tools.protoc',
                '-I', "./",
                '--python_out', ".",
                '--grpc_python_out', ".",
                *protos
            ]
            cmds = " ".join(cmd)
            os.system(cmds)

    if finisheds:
        for msg in finisheds:
            print(f" {msg}       OK")
    else:
        print(f" Not find the proto file\n")

    return 0


@cli.command('test', env='test', app=False, help='run test')
def runtest(argv, **extra):
    import pytest
    from binwen import create_app

    class AppPlugin:

        def pytest_load_initial_conftests(early_config, parser, args):
            create_app()

    return pytest.main(argv, plugins=[AppPlugin])


@cli.command('createproject', app=False, help='Create Binwen Project')
@cli.option('project', help='project name')
@cli.option('--skip-git', action='store_true', help='skip add git files and run git init')
@cli.option('--skip-cache', action='store_true', help='skip cache')
@cli.option('--skip-celery', action='store_true', help='skip celery')
def create_project(project, **extra):
    import shutil
    from jinja2 import Environment, FileSystemLoader
    path = os.path.join(os.getcwd(), project)
    if os.path.exists(path):
        raise CommandException('{} already exists'.format(path))

    template_path = os.path.join(os.path.dirname(__file__), 'template', 'project_tpl')
    ignored_files = {
        'git': ['.gitignore'],
        'celery': ['tasks/__init__.py.tmpl'],
    }
    skip_files = set()
    for k, files in ignored_files.items():
        if not extra[f'skip_{k}']:
            continue
        for f in files:
            skip_files.add(os.path.join(template_path, f))

    env = Environment(loader=FileSystemLoader(template_path))
    ctx = extra.copy()
    ctx['project'] = os.path.basename(path)

    for dirpath, dirnames, filenames in os.walk(template_path):
        for fn in filenames:
            src = os.path.join(dirpath, fn)
            if src in skip_files:
                continue

            relftp = os.path.relpath(src, template_path)
            dst = os.path.join(path, relftp)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            r, ext = os.path.splitext(dst)
            if ext == '.tmpl':
                with open(r, 'w') as f:
                    tmpl = env.get_template(relftp)
                    f.write(tmpl.render(**ctx))
            else:
                shutil.copyfile(src, dst)

            print(f' {r}         OK')

    print(f'\n\ncreated project finished: {path}')

    return 0


@cli.command('createapp', app=False, help='Create Binwen Project App')
@cli.option('app', help='app name')
@cli.option('--proto', type=str, help='app proto name')
@cli.option('--skip-orm', action='store_true', help='skip orm')
def create_app(app, proto=None, **extra):
    import shutil
    from jinja2 import Environment, FileSystemLoader
    path = os.path.join(os.getcwd(), app)
    if os.path.exists(path):
        raise CommandException('{} already exists'.format(path))

    if not os.path.exists(os.path.join(os.getcwd(), "app.py")):
        raise CommandException('Please execute this command in the project root directory')

    template_path = os.path.join(os.path.dirname(__file__), 'template', 'app_tpl')
    env = Environment(loader=FileSystemLoader(template_path))
    ctx = extra.copy()
    app_proto = proto if proto else app
    ctx['app_proto'] = app_proto

    ignored_files = {
        'orm': ['models.py.tmpl'],
    }
    skip_files = set()
    for k, files in ignored_files.items():
        if not extra[f'skip_{k}']:
            continue
        for f in files:
            skip_files.add(os.path.join(template_path, f))

    for dirpath, dirnames, filenames in os.walk(template_path):
        for fn in filenames:
            src = os.path.join(dirpath, fn)
            if src in skip_files:
                continue

            relftp = os.path.relpath(src, template_path)
            dst = os.path.join(path, relftp)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            r, ext = os.path.splitext(dst)
            if ext == '.tmpl':
                if r.endswith(".proto"):
                    r = f"{r[:-9]}{app_proto}.proto"

                with open(r, 'w') as f:
                    tmpl = env.get_template(relftp)
                    f.write(tmpl.render(**ctx))
            else:
                shutil.copyfile(src, dst)

            print(f' {r}         OK')
    try:
        with open(os.path.join(os.getcwd(), "extensions.py"), "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    with open(os.path.join(os.getcwd(), "extensions.py"), "w") as f:
        temp_lines = ";".join(lines)
        if "PeeweeExt()" not in temp_lines:
            lines.insert(0, 'from peeweext.binwen import PeeweeExt\n')
            lines.insert(len(lines), '\ndb = PeeweeExt()\n')
        f.writelines(lines)
        print(f' Initialize `PeeweeExt` in the `extensions.py` file          OK')

    try:
        with open(os.path.join(os.getcwd(), "requirements.txt"), "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    with open(os.path.join(os.getcwd(), "requirements.txt"), "w") as f:
        temp_lines = [l.strip() for l in lines]
        if "binwen-peewee" not in temp_lines:
            lines.insert(len(lines), '\nbinwen-peewee\n')
        f.writelines(lines)
        print(f' Add the `binwen-peewee` library package to the `requirements.txt` file      OK')

    print(f'\n\ncreated app finished: {path}')

    return 0
