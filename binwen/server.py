import sys
import time
import signal
import logging
from concurrent import futures

import grpc

from binwen import signals


class Server:

    def __init__(self, app, addrport=None, workers=3):
        self.app = app
        self.setup_logger()
        self.workers = workers
        self.addrport = addrport if addrport else "[::]:50051"
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=self.workers))
        self.server.add_insecure_port(self.addrport)
        self._stopped = False

    def run(self):
        for name, (add_func, servicer) in self.app.servicers.items():
            add_func(servicer(), self.server)
        self.server.start()
        signals.server_started.send(self)
        self.register_signal()
        quit_command = 'CTRL-BREAK' if sys.platform == 'win32' else 'CONTROL-C'
        sys.stdout.write(f"Starting development server at {self.addrport}\n Quit the server with {quit_command}.\n")
        while not self._stopped:
            time.sleep(1)
        signals.server_stopped.send(self)
        return True

    def setup_logger(self):
        fmt = self.app.config['GRPC_LOG_FORMAT']
        lvl = self.app.config['GRPC_LOG_LEVEL']
        h = self.app.config['GRPC_LOG_HANDLER']
        h.setFormatter(logging.Formatter(fmt))
        logger = logging.getLogger()
        logger.setLevel(lvl)
        logger.addHandler(h)

    def register_signal(self):
        signal.signal(signal.SIGINT, self._stop_handler)
        signal.signal(signal.SIGHUP, self._stop_handler)
        signal.signal(signal.SIGTERM, self._stop_handler)
        signal.signal(signal.SIGQUIT, self._stop_handler)

    def _stop_handler(self, signum, frame):
        grace = self.app.config['GRPC_GRACE']
        self.server.stop(grace)
        time.sleep(grace or 1)
        self._stopped = True
