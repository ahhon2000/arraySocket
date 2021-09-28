from collections import namedtuple

UserAuthStatus = namedtuple('UserAuthStatus', ('status', 'descr'))

class ServerMessageArray:
    def __init__(self, cli, ms):
        self.logger = cli.logger

        if(not isinstance(ms, list)): raise Exception('data received from the server is not an array')

        self.cli = cli
        self.messages = list(ms)

    def processMessages(self):
        ms = self.messages
        for m in ms:
            self.processMessage1(m)

    def processMessage1(self, m):
        if not isinstance(m, dict): raise Exception('server message not a dict')

        cli = self.cli

        typ = m.get('type')

        with cli.concur:
            if typ not in cli.concur.MSG_TYPES_SRV: 
                self.logger.warning(f'unsupported server message type: {typ}')

        handler = getattr(self, 'on_' + typ)
        if not handler: raise Exception(f'no handler for server message type {typ}')
        handler(m)
        self.execCallback(m)

    def execCallback(self, m):
        cbk = m.get('callback')
        if not cbk: return

        cmaRef = m.get('clientMessageArray', '')
        if not cmaRef: raise Exception(f'cannot execute the callback without a reference to the client message array')

        cma = fzh.concur.clientMessageArrays.get(cmaRef, '')
        if not cma: raise Exception(f'the callback requested by the server is unavailable (no client message array)')

        cma.execCallback(cbk, m)

    def on_auth(self, m):
        """Process an auth-type message

        Return a named tuple (status, descr) where status is the authentication
        status returned by the server and descr is that status's description
        """

        cli = self.cli

        S = UserAuthStatus
        s = S(m.get('status'), m.get('descr', ''))

        if s.status is None:
            raise Exception('the server returned no authentication status');
        elif s.status == 0:
            for k in ('MSG_TYPES_SRV', 'MSG_TYPES_CLI'):
                mts0 = m.get(k)
                if mts0 is None: raise Exception('the server did not provide ' + k + ' on authentication')

                cli.setMsgTypes(k, mts0)
        else:
            descr = f': {s.descr}' if s.descr else ''
            self.logger.debug(f'authentication failed (status={s.status}){descr}')
        return s

    def on_error(self, m):
        descr = m.get('descr', '')
        self.logger.error(f'server error: {descr}')
