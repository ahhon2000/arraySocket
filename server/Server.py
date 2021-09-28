from collections import namedtuple
import socketio
from pathlib import Path

from BaseClientServer import BaseClientServer

DEFAULT_PORT = 5490
DEFAULT_PORT2 = 5491

UserAuthStatus = namedtuple('UserAuthStatus', ('status', 'descr', 'user'))

class Server(BaseClientServer):
    def __init__(self,
        staticUsers = (),
        authEveryone = False,  # grants access to all users
        allowCors = True,
        authUsersInMem = False,
        **kwarg
    ):
        super().__init__(isServer=True, **kwarg)

        if allowCors:
            self.sock_kwarg['cors_allowed_origins'] = '*'

        self.sock = sock = socketio.Server(**self.sock_kwarg)
        self._setupSocketHandlers()

        # Generally, it's a bad idea to maintain a large table of users in
        # memory. The attribute `staticUsers' is meant to consist of a
        # small number of embedded users (like admin), or for tests.
        #
        # Each entry in staticUsers maps a user's name to an ASUser object.
        self.staticUsers = {u.name: u for u in staticUsers}
        self._authUsers = {}  # format:  sid: ASUser

        self.authEveryone = authEveryone
        self.authUsersInMem = authUsersInMem

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
            self.rmAuthUser(sid)
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

    def checkUserCredentials(self, name, authKey):
        """Check if a user may access the server

        NOTE: For custom user lookups (e. g. in a DB) override lookupUser()
        instead of this function

        Return value: a named tuple (status, descr, user)

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

    def saveAuthUser(self, sid, u):
        """Save a sid-user association to an internal table (or elsewhere)

        This method is called once the user has been successfully authenticated
        to authorise further message arrays from the same socket.

        The sid-user pair will be stored in memory only if the
        authUsersInMem setting is True.

        For a custom way of handling sid-user pairs (say, with a DB),
        override this method.
        """

        if self.authUsersInMem:
            self._authUsers[sid] = u

    def lookupAuthUser(self, sid):
        """Search the (internal) table for an authenticated user by their sid

        Override if a different mechanism of storing sid-user pairs is used.
        """

        u = None
        if self.authUsersInMem:
            u = self._authUsers.get(sid)

        return u

    def rmAuthUser(self, sid):
        self._authUsers.pop(sid, None)
