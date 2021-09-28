from collections import namedtuple
import socketio
from pathlib import Path

from BaseClientServer import BaseClientServer

DEFAULT_PORT = 5490
DEFAULT_PORT2 = 5491

UserAuthStatus = namedtuple('UserAuthStatus', ('status', 'descr', 'user'))

class Server(BaseClientServer):
    def __init__(self,
        staticUsers=(),
        authEveryone=False,
        allowCors=True,
        **kwarg
    ):
        super().__init__(isServer=True, **kwarg)

        if allowCors:
            self.sock_kwarg['cors_allowed_origins'] = '*'

        self.sock = sock = socketio.Server(**self.sock_kwarg)
        self._setupSocketHandlers()

        # Generally, it's a bad idea to maintain a large table of users in
        # memory. The attribute `staticUsers' is meant to consist of
        # small number of embedded user (like admin), or for tests.
        #
        # Each entry in staticUsers maps a user's name to an ASUser object.
        self.staticUsers = {u.name: u for u in staticUsers}
        self.authEveryone = authEveryone

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
            print('disconnect ', sid)  # TODO replace with proper logging

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

    def checkUserCredentials(self, name, authKey):
        """Check if a user may access the server

        NOTE: for custom user lookups (e. g. in a DB) override lookupUser()

        Return a named tuple (status, descr, user)

        status is 0 iff access is granted
        descr is a short description of the status.
        user is the user object
        """

        S = UserAuthStatus
        s = S(127, 'unknown authentication error', None)

        u = self.staticUsers.get(name)
        if not u:
            u = self.lookupUser(name)

        if self.authEveryone:  # for tests
            s = S(0, 'success', u)
        elif not name:
            s = S(1, 'no user', u)
        else:
            if not authKey:
                s = S(2, 'no authentication key', u)
            else:
                s = S(3, 'wrong credentials', u)
                if u:
                    if name == u.name  and  authKey == u.authKey:
                        s = S(0, 'success', u)

        return s

    def lookupUser(self, name):
        "Override this method for custom user lookups. Should return an ASUser"

        return None
