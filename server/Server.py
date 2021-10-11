from collections import namedtuple
import socketio
from pathlib import Path
from enum import Enum

from .. import BaseClientServer
from handyPyUtil.loggers.convenience import fmtExc
from handyPyUtil.classes import DictToObject

DEFAULT_PORT = 5490
DEFAULT_PORT2 = 5491

class SRV_ERR_MSG_CODES(Enum):
    srv_msg_error = 1
    unsupported_msg_type = 2
    access_denied = 3
    general_error = 127

class ServerError(Exception):
    def __init__(self, m, code=SRV_ERR_MSG_CODES.general_error, **kwarg):
        super().__init__(f'{m} (code={code.value})', **kwarg)
        self.code = code

class ServerErrorSrvMsg(ServerError):
    def __init__(self, m):
        super().__init__(m, code = SRV_ERR_MSG_CODES.srv_msg_error)

class ServerErrorUnsupported(ServerError):
    def __init__(self, m):
        super().__init__(m, code = SRV_ERR_MSG_CODES.unsupported_msg_type)

class ServerErrorAccessDenied(ServerError):
    def __init__(self, m):
        super().__init__(m, code = SRV_ERR_MSG_CODES.access_denied)


class Server(BaseClientServer):
    def __init__(self,
        usersStorage = 'db',
        dbobj = None,
        read_default_file = None,
        adminAuthKey = '',
        staticUsers = (),
        authEveryone = False,  # grants access to all users
        authUsersInMem = False,
        allowCors = True,
        AdminInterfaceCls = None,
        UsersTblCls = None,
        usersTbl_kwarg = {},
        **kwarg
    ):
        """Initialise an Array Socket server instance

        usersStorage can be 'memory' or 'db', which controls where to store
        the users table. Note that if UsersTBlCls is supplied it will
        override whatever value the usersStorage parameter has.

        The argument `dbobj' can be supplied to give the users table a Database
        instance to work with. If `dbobj' is not given a new Database object
        will be initialised.

        UsersTblCls can be given, optionally along with keyword arguments
        `usersTbl_kwarg' to pass on to its constructor.

        For a database users table storage method, a *.cnf file can be specified
        as the `read_default_file' argument. This file will be used for
        database initialisation. It can be a string or a Path object.

        If adminAuthKey is given and is not empty add that string to the set of
        keys of user `admin'. If user `admin' doesn't exist create it.
        All previous keys (if any) will be removed.
        """

        super().__init__(isServer=True, **kwarg)

        ik = DictToObject(locals())

        self._initAdminInterface(ik)
        self._initUsersTbl(ik)

        if allowCors:
            self.sock_kwarg['cors_allowed_origins'] = '*'

        # Init the socket and the app object

        self.sock = sock = socketio.Server(**self.sock_kwarg)
        self._setupSocketHandlers()

        self.app = app = socketio.WSGIApp(sock,
            static_files = {
                '/': {'content_type': 'text/html', 'filename': 'index.html'},
            }
        )

    def _initAdminInterface(self, ik):
        if not ik.AdminInterfaceCls:
            from . import AdminInterface
            ik.AdminInterfaceCls = AdminInterface
        self.adminInterface = ik.adminInterface = ik.AdminInterfaceCls(self)

    def _initUsersTbl(self, ik):
        if ik.dbobj and ik.read_default_file: raise Exception(f'keyword arguments dbobj, read_default_file are incompatible')
        if ik.dbobj and ik.UsersTblCls: raise Exception(f'keyword arguments dbobj, UsersTblCls are incompatible')

        if not ik.UsersTblCls:
            if ik.usersStorage == 'memory':
                from . import UsersTbl
                ik.UsersTblCls = UsersTbl
            elif ik.usersStorage == 'db':
                from .dbUsersTbl import DBUsersTbl
                ik.UsersTblCls = DBUsersTbl
            else: raise Exception(f'unsupported value of argument "usersStorage": {usersStorage}')

        ik.usersTbl_kwarg = dict(
            {
                'staticUsers': ik.staticUsers,
                'authEveryone': ik.authEveryone,
                'authUsersInMem': ik.authUsersInMem,
            },
            **ik.usersTbl_kwarg
        )

        if ik.read_default_file:
            ik.usersTbl_kwarg.setdefault('db_kwarg', {})
            ik.usersTbl_kwarg['db_kwarg']['read_default_file'] = str(ik.read_default_file)
        if ik.dbobj:
            ik.usersTbl_kwarg['dbobj'] = ik.dbobj


        self.usersTbl = ik.usersTbl = ik.UsersTblCls(self, **ik.usersTbl_kwarg)
        if ik.adminAuthKey:
            ik.usersTbl.rmAllAuthKeys('admin')
            ik.usersTbl.addAuthKey('admin', ik.adminAuthKey, isAdmin=True)

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
                    'descr': fmtExc(e, inclTraceback=self.debug),
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
