import socketio
from pathlib import Path
import threading

from . import ServerMessageArray
from . import ClientMessageArray

DEFAULT_PORT = 5490
DEFAULT_PORT2 = 5491

class Server:
    def __init__(self, debug=False, allowCors=True, **sock_kwarg):
        if allowCors:
            sock_kwarg['cors_allowed_origins'] = '*'

        self.stopEvent = threading.Event()

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
            print('connect ', sid)

        @sock.event
        def client_message_array(sid, data):
            if self.stopEvent.isSet():
                import eventlet
                raise eventlet.StopServe()

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
            print('disconnect ', sid)

    def run(self, method="eventlet", **kwarg):
        if method == "eventlet":
            self._runEventlet(**kwarg)
        else: raise Exception(f"unsupported method of running the surver: {method}")

    def _runEventlet(self,
        useUnixSocket=False, sockPath="", port=DEFAULT_PORT2,
    ):
        import eventlet
        l = None
        if useUnixSocket:
            sockPath = str(sockPath)
            l = eventlet.listen(sockPath, eventlet.wsgi.socket.AF_UNIX)
        elif self.debug:
            l = eventlet.listen(('127.0.0.1', DEFAULT_PORT))
        else:
            l = eventlet.listen(('127.0.0.1', port))

        eventlet.wsgi.server(l, self.app)
