from collections import namedtuple
import socketio
from pathlib import Path
from enum import Enum

from .. import BaseClientServer
from handyPyUtil.loggers.convenience import fmtExc

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
        usersTbl = None,
        staticUsers = (),
        authEveryone = False,  # grants access to all users
        authUsersInMem = False,
        allowCors = True,
        AdminInterfaceCls = None,
        UsersTblCls = None,
        usersTbl_kwarg = {},
        **kwarg
    ):
        super().__init__(isServer=True, **kwarg)

        if allowCors:
            self.sock_kwarg['cors_allowed_origins'] = '*'

        # init the admin interface
        if not AdminInterfaceCls:
            from . import AdminInterface
            AdminInterfaceCls = AdminInterface
        self.adminInterface = adminInterface = AdminInterfaceCls(self)

        self.sock = sock = socketio.Server(**self.sock_kwarg)
        self._setupSocketHandlers()

        # init the users table
        if not UsersTblCls:
            from . import UsersTbl
            UsersTblCls = UsersTbl
        usersTbl_kwarg = dict(
            {
                'staticUsers': staticUsers,
                'authEveryone': authEveryone,
                'authUsersInMem': authUsersInMem,
            },
            **usersTbl_kwarg
        )
        self.usersTbl = usersTbl = UsersTblCls(self, **usersTbl_kwarg)

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
