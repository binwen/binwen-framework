import os
import signal
import threading
from unittest import mock

from binwen.server import Server
from binwen.signals import server_started, server_stopped


def test_server(app, log_stream):
    s = Server(app)
    assert not s._stopped

    def log_started(s):
        app.logger.warn('started!')

    def log_stopped(s):
        app.logger.warn('stopped!')

    server_started.connect(log_started)
    server_stopped.connect(log_stopped)

    with mock.patch('time.sleep', new=lambda s: os.kill(os.getpid(), signal.SIGINT)):
        assert s.run()
        assert threading.active_count() == 1
        assert s._stopped

    content = log_stream.getvalue()
    assert 'started!' in content and 'stopped!' in content
