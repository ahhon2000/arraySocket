from collections import namedtuple
import socketio
from pathlib import Path

from .. import BaseClientServer
from .UsersTbl import UsersTbl

DEFAULT_PORT = 5490
DEFAULT_PORT2 = 5491

class Server(BaseClientServer):
    def __init__(self,
        usersTbl = None,
        staticUsers = (),
        authEveryone = False,  # grants access to all users
        authUsersInMem = False,
        allowCors = True,
        **kwarg
    ):
        super().__init__(isServer=True, **kwarg)

        if allowCors:
            self.sock_kwarg['cors_allowed_origins'] = '*'

        self.sock = sock = socketio.Server(**self.sock_kwarg)
        self._setupSocketHandlers()

        if not usersTbl:
            usersTbl = UsersTbl(
                staticUsers = staticUsers,
                authEveryone = authEveryone,
                authUsersInMem = authUsersInMem,
            )
        self.usersTbl = usersTbl

        self.app = app = socketio.WSGIApp(sock,
            static_files = {
                '/': {'content_type': 'text/html', 'filename': 'index.html'},
            }
        )

    def _setupSocketHandlers(self):
        sock = self.sock

        @sock.event
        def connect(sid, environ):
            self.logger.info(f'a user connected, sid={sid}')

        @sock.event
        def client_message_array(sid, data):
            try:
                cma = self.CMAClass(self, sid, data)
                cma.processMessages()
            except Exception as e:
                m = {
                    'type': 'error',
                    'descr': str(e),
                }
                sma = self.SMAClass(self, sid, [m])
                sma.send()
            return "ack"

        @sock.event
        def disconnect(sid):
            self.usersTbl.rmAuthUser(sid)
            self.logger.info(f'user with sid={sid} disconnected')

    def run(self, method="eventlet", **kwarg):
        if method == "eventlet":
            self._runEventlet(**kwarg)
        else: raise Exception(f"unsupported method of running the surver: {method}")

    def _runEventlet(self,
        addr="127.0.0.1", port=None,
        useUnixSocket=False,
        sockPath="",
    ):

        import eventlet
        l = None
        if useUnixSocket:
            sockPath = str(sockPath)
            l = eventlet.listen(sockPath, eventlet.wsgi.socket.AF_UNIX)
        else:
            if not port:
                port = DEFAULT_PORT if self.debug else DEFAULT_PORT2
            l = eventlet.listen((addr, port))

        self._listener = l

        eventlet.wsgi.server(l, self.app)
