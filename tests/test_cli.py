import os
import sys
import shutil
from unittest import mock

import pytest

from binwen import cli


def test_server(app):
    sys.argv = 'bw run'.split()
    with mock.patch('binwen.commands.Server', autospec=True) as mocked:
        assert cli.main() == 0
        mocked.return_value.run.assert_called_with()


def test_shell(app):
    sys.argv = 'bw shell'.split()
    mocked = mock.MagicMock()
    with mock.patch.dict('sys.modules', {'IPython': mocked}):
        assert cli.main() == 0
        assert mocked.embed.called


def test_make(app):
    sys.argv = 'bw make'.split()
    with mock.patch('os.getcwd', return_value=app.root_path):
        os.chdir("tests/demo")
        # with mock.patch('grpc_tools.protoc.main', return_value=0) as mocked:
        assert cli.main() == 0
        sys.argv = 'bw make hw2.proto'.split()
        assert cli.main() == 0
        for fn in ("hw/hw", "helloworld"):
            assert os.path.exists(f'./hw2/proto/{fn}_pb2.py')
            os.remove(f'./hw2/proto/{fn}_pb2.py')
            os.remove(f'./hw2/proto/{fn}_pb2_grpc.py')
            assert not os.path.exists(f'./hw2/proto/{fn}_pb2.py')


def test_createproject():
    shutil.rmtree('tests/myproject', ignore_errors=True)
    sys.argv = 'bw createproject tests/myproject --skip-git'.split()
    assert cli.main(raise_exception=False) == 0
    correct_code = """\
    from cachext.exts import Cache
    from binwen.contrib.extensions.celery import Celery


    cache = Cache()
    celeryapp = Celery()
    """
    with open('./tests/myproject/extensions.py', 'r') as f:
        content = f.read()

    from textwrap import dedent
    assert content.strip() == dedent(correct_code).strip()
    assert not os.path.exists('./tests/myproject/config/project.py')
    assert os.path.exists('./tests/myproject/config/dev.py')
    assert os.path.exists('./tests/myproject/app.py')

    correct_code = """\
    binwen-framework
    cachext
    celery
    """
    with open('./tests/myproject/requirements.txt', 'r') as f:
        content = f.read()
    assert content.strip() == dedent(correct_code).strip()

    shutil.rmtree('tests/myproject')


def test_createapp(app):
    with mock.patch('os.getcwd', return_value=app.root_path):
        try:
            os.chdir("tests/demo")
        except FileNotFoundError:
            pass

        shutil.rmtree('myapp', ignore_errors=True)
        sys.argv = 'bw createapp myapp --proto=test'.split()
        assert cli.main(raise_exception=False) == 0
        correct_code = """\
        # from .proto import test_pb2
        # from .proto import test_pb2_grpc
        
        # from binwen.servicer import ServicerMeta
        
        
        # class TestServicer(test_pb2_grpc.TestServicer, metaclass=ServicerMeta):
        
        #     pass
        """
        with open('./myapp/servicers.py', 'r') as f:
            content = f.read()

        from textwrap import dedent
        assert content.strip() == dedent(correct_code).strip()
        assert os.path.exists('./myapp/proto/test.proto')
        with open("./extensions.py", "r") as f:
            content = f.read()
        assert "from peeweext.binwen import PeeweeExt" in content
        shutil.rmtree('myapp')
        os.chdir(app.root_path)


def test_cli_command(app):
    with mock.patch('os.getcwd', return_value=app.root_path):
        sys.argv = 'bw plusone -n 100'.split()
        assert cli.main() is None
        assert app.config.get('NUMBER') == 101
        sys.argv = 'bw config_hello'.split()
        assert isinstance(cli.main(), cli.CommandException)

    class EntryPoint:
        def load(self):
            @cli.cli.command('xyz')
            def f2(**kwargs):
                app.config['XYZ'] = 'hello'
            return f2

    def new_entry_iter(name):
        return [EntryPoint()]

    with mock.patch('pkg_resources.iter_entry_points', new=new_entry_iter):
        sys.argv = 'bw xyz'.split()
        assert cli.main() is None
        assert app.config.get('XYZ') == 'hello'


def test_main():
    sys.argv = 'bw -h'.split()
    with pytest.raises(SystemExit):
        cli.main()
    sys.argv = ['bw']
    with pytest.raises(SystemExit):
        cli.main()
