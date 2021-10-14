from handyPyUtil.loggers import fmtExc

from .. import BaseMessageArray
from .Server import (
    SRV_ERR_MSG_CODES, ServerError, ServerErrorAccessDenied,
    ServerErrorUnsupported,
)

class ClientMessageArray(
    BaseMessageArray.cloneClass(
        set_MSG_TYPES = ('admin', 'auth', 'echo'),
    )
):
    def __init__(self, srv, sid, ms):
        self.logger = srv.logger

        self.sid = sid
        self.messages = list(ms)
        self.srv = srv

        self.serverMessageArray = None
        self._newServerMessageArray()

        self.user = u = srv.usersTbl.lookupAuthUser(
            sid=sid, renewExpiryIfFound=True
        )

        self.isAuthenticated = True if u else False

    def _newServerMessageArray(self):
        srv = self.srv
        sid = self.sid
        self.serverMessageArray = srv.SMAClass(srv, sid)

    def processMessages(self):
        srv = self.srv
        ms = self.messages

        for m in ms:
            try:
                self._processMessage1(m)
            except Exception as e:
                code = SRV_ERR_MSG_CODES.general_error
                if isinstance(e, ServerError):
                    code = e.code

                s = fmtExc(e, inclTraceback=srv.debug)
                self.pushErrorMessage(s, code=code)

        self.sendMessages()

    def _processMessage1(self, m):
        if not isinstance(m, dict): raise Exception('client message not a dictionary')
        typ = m.get('type')
        if typ not in self.MSG_TYPES:
            raise ServerErrorUnsupported(
                f'unsupported message type: {typ}',
                code = SRV_ERR_MSG_CODES.unsupported_msg_type
            )

        if not self.isAuthenticated  and  typ != 'auth':
            raise ServerErrorAccessDenied(f'Access denied')

        h = getattr(self, 'on_' + typ, None)
        if not h: raise Exception(f'no handler for message type={typ}')
        self.logger.debug(f'processing client message type={typ}')
        h(m)

    def on_admin(self, m):
        srv = self.srv
        u = self.user
        if not self.isAuthenticated or not u:
            raise ServerErrorAccessDenied(
                f'access to the admin interface denied: anonymous user',
            )
        if not u.isAdmin: raise Exception(f'the user is not an admin')

        srv.adminInterface.processMessage(self, m)

    def on_auth(self, m):
        srv = self.srv

        name, authKey = map(lambda k: m.get(k, ''), ('user', 'authKey'))
        srv.logger.debug(f"received authentication request from user `{name}'; authKey length = {len(authKey)}")

        s = srv.usersTbl.checkUserCredentials(name, authKey)
        self.user = s.user
        if s.status == 0:
            self.isAuthenticated = True
            srv.usersTbl.saveAuthUser(sid=self.sid, user=s.user)

        self.pushMessage({
            'type': 'auth',
            'status': s.status,
            'descr': s.descr,
            'MSG_TYPES_CLI': srv.CMAClass.MSG_TYPES,
            'MSG_TYPES_SRV': srv.SMAClass.MSG_TYPES,
        })

    def on_echo(self, m):
        mrsp = dict(m)
        self.pushMessage(mrsp, cbFromCliMsg=m, ignoreMissingCallback=True)

    def pushErrorMessage(self, descr, code=SRV_ERR_MSG_CODES.general_error):
        sma = self.serverMessageArray
        sma.pushErrorMessage(descr, code=code)

    def pushMessage(self, m, **kwarg):
        sma = self.serverMessageArray
        sma.pushMessage(m, **kwarg)

    def sendMessages(self):
        sma = self.serverMessageArray
        sma.send()
        self._newServerMessageArray()
