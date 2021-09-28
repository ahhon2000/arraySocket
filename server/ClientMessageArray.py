from handyPyUtil.loggers import fmtExc
class ClientMessageArray:
    MSG_TYPES_CLI = ('admin', 'auth',)

    def __init__(self, srv, sid, ms):
        self.logger = srv.logger

        self.sid = sid
        self.messages = list(ms)
        self.srv = srv

        self.serverMessageArray = None
        self._newServerMessageArray()

        self.user = u = srv.lookupAuthUser(sid)
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
                s = fmtExc(e, inclTraceback=srv.debug)
                self.pushErrorMessage(s)

        self.sendMessages()

    def _processMessage1(self, m):
        if not isinstance(m, dict): raise Exception('client message not a dictionary')
        typ = m.get('type')
        if typ not in self.MSG_TYPES_CLI:
            raise Exception(f'unsupported message type: {typ}')

        if not self.isAuthenticated  and  typ != 'auth':
            raise Exception(f'Access denied')

        h = getattr(self, 'on_' + typ, None)
        if not h: raise Exception(f'no handler for message type={typ}')
        self.logger.debug(f'processing client message type={typ}')
        h(m)

    def on_admin(self, m):
        pass

    def on_auth(self, m):
        srv = self.srv

        name, authKey = map(lambda k: m.get(k, ''), ('user', 'authKey'))
        srv.logger.debug(f"received authentication request from user `{name}'; authKey length = {len(authKey)}")

        s = srv.checkUserCredentials(name, authKey)
        self.user = s.user
        if s.status == 0:
            self.isAuthenticated = True
            srv.saveAuthUser(self.sid, s.user)

        self.pushMessage({
            'type': 'auth',
            'status': s.status,
            'descr': s.descr,
            'MSG_TYPES_CLI': srv.CMAClass.MSG_TYPES_CLI,
            'MSG_TYPES_SRV': srv.SMAClass.MSG_TYPES_SRV,
        })

    def on_draw(self, m):
        self.pushErrorMessage('unimplemented method')

    def pushErrorMessage(self, descr):
        sma = self.serverMessageArray
        sma.pushErrorMessage(descr)

    def pushMessage(self, m):
        sma = self.serverMessageArray
        sma.pushMessage(m)

    def sendMessages(self):
        sma = self.serverMessageArray
        sma.send()
        self._newServerMessageArray()
