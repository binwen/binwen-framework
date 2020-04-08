from peeweext.binwen import PeeweeExt
# from cachext.exts import Cache
from binwen.contrib.extensions.celery import Celery


# cache = Cache()
celeryapp = Celery()

db = PeeweeExt()
