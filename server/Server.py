import socketio
from pathlib import Path

from . import ServerMessageArray
from . import ClientMessageArray

DEFAULT_PORT = 5490
DEFAULT_PORT2 = 5491

class Server:
    def __init__(self, debug=False, allowCors=True, **sock_kwarg):
        if allowCors:
            sock_kwarg['cors_allowed_origins'] = '*'

        self.debug = debug
        self.sock = sock = socketio.Server(**sock_kwarg)
        self._setupSocketHandlers()

        self.app = app = socketio.WSGIApp(sock,
            static_files = {
                '/': {'content_type': 'text/html', 'filename': 'index.html'},
            }
        )

    def _setupSocketHandlers(self):
        sock = self.sock

        @sock.event
        def connect(sid, environ):
            print('connect ', sid)  # TODO replace with proper logging

        @sock.event
        def client_message_array(sid, data):
            try:
                cma = ClientMessageArray(self, sid, data)
                cma.processMessages()
            except Exception as e:
                m = {
                    'type': 'error',
                    'descr': str(e),
                }
                sma = ServerMessageArray(self, sid, [m])
                sma.send()
            return "ack"

        @sock.event
        def disconnect(sid):
            print('disconnect ', sid)  # TODO replace with proper logging

    def run(self, method="eventlet", **kwarg):
        if method == "eventlet":
            self._runEventlet(**kwarg)
        else: raise Exception(f"unsupported method of running the surver: {method}")

    def _runEventlet(self,
        addr="127.0.0.1", port=DEFAULT_PORT2,
        useUnixSocket=False,
        sockPath="",
    ):
        import eventlet
        l = None
        if useUnixSocket:
            sockPath = str(sockPath)
            l = eventlet.listen(sockPath, eventlet.wsgi.socket.AF_UNIX)
        elif self.debug:
            l = eventlet.listen((addr, DEFAULT_PORT))
        else:
            l = eventlet.listen((addr, port))

        self._listener = l

        eventlet.wsgi.server(l, self.app)
