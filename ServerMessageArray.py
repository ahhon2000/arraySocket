class ServerMessageArray:
    def __init__(self, fzhc, ms):
        if(not isinstance(ms, list)): raise Exception('data received from the server is not an array')

        self.flazhClient = fzhc
        self.messages = list(ms)

    def processMessages(self):
        ms = self.messages
        for m in ms:
            self.processMessage1(m)

    def processMessage1(self, m):
        if not isinstance(m, dict): raise Exception('server message not a dict')

        fzhc = this.flazhClient

        typ = m.get('type')

        with fzhc.concur:
            if typ in fzhc.concur.MSG_TYPES_SRV: 
                print(f'warning: unsupported server message type: {typ}')

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
        fzhc = self.flazhClient
        st = m.get('status')

        if st is None:
            raise Exception('the server returned no authentication status');
        elif st == 0:
            for k in ('MSG_TYPES_SRV', 'MSG_TYPES_CLI'):
                mts0 = m.get(k)
                if mts0 is None: raise Exception('the server did not provide ' + k + ' on authentication')

                fzhc.setMsgTypes(k, mts0)
        else:
            descr = f': {m.descr}' if m.descr else ''
            raise Exception(f'authentication failed (status={st}){descr}');

    def on_error(self, m):
        descr = m.get('descr', '')
        print(f'server error: {descr}')
