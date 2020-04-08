import os
import json

from binwen.config import ConfigAttribute, Config

TEST_KEY = 'foo'
SECRET_KEY = 'config'


def common_object_test(app):
    assert app.config.secret_key == 'config'
    assert app.config['TEST_KEY'] == 'foo'
    assert app.config['tEST_KEY'] == 'foo'
    assert 'tEST_KEY' in app.config
    assert 'TestConfig' not in app.config


def test_config_from_object(app):
    app.config.from_object(__name__)
    common_object_test(app)


def test_config_from_class(app):
    class Base:
        TEST_KEY = 'foo'
        TEST_VALUE = 'bar'

    class Test(Base):
        DEBUG = True
        SECRET_KEY = 'config'

    config = Config({'DEBUG': False})

    assert config['DEBUG'] is False
    config.from_object(Test)
    assert config['DEBUG'] is True

    assert config['TEST_KEY'] == 'foo'
    assert 'TestConfig' not in config
    d = config.get_namespace('TEST_')
    assert 'key' in d
    assert 'value' in d
    d = config.get_namespace('TEST_', lowercase=False, trim_namespace=False)
    assert 'TEST_KEY' in d
    s = repr(config)
    assert '<Config' in s
    app.config.from_object(Test)
    common_object_test(app)


def test_config_from_json(app):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app.config.from_json(os.path.join(current_dir, 'config.json'))
    common_object_test(app)


def test_config_from_mapping(app):
    app.config.from_mapping({
        'SECRET_KEY': 'config',
        'TEST_KEY': 'foo'
    })
    common_object_test(app)

    app.config.from_mapping(
        SECRET_KEY='config',
        TEST_KEY='foo'
    )
    common_object_test(app)


def test_config_attribute():
    class App:
        x = ConfigAttribute('n_x', json.loads)

    assert type(App.x) == ConfigAttribute
    a = App()
    a.config = Config({'n_x': json.dumps({'foo': 'bar'})})
    assert 'foo' in a.x
    a.x = json.dumps({'a': 1})
    assert 'a' in a.config['n_x']
