import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TESTING = False
DEBUG = True

INSTALLED_APPS = ["helloworld"]

MIDDLEWARE = [
    'binwen.middleware.ServiceLogMiddleware',
    'binwen.middleware.RpcErrorMiddleware',
]

DATABASES = {
    "default": {
      "DB_URL": "sqlite:///:memory:",
      "CONN_OPTIONS": {}
    }
}
# 具体配置见celery 文档(http://docs.celeryproject.org/en/v4.1.0/userguide/configuration.html)
CELERY_BROKER_URL = 'redis://localhost:6379/1'
CELERY_IMPORTS = ['tasks']

