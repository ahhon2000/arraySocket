from handyPyUtil.loggers import fmtExc

class AdminInterface:
    def __init__(self, srv=None):
        self.srv = srv
        self.logger = srv.logger

    def processMessage(cma, m):
        srv = self.srv

        try:
            cmd = m.get('command', '')
            if not cmd: raise Exception(f'no command given')

            h = getattr(self, f'cmd_{cmd}', None)
            if not h: raise Exception(f'unsupported admin command: {cmd}')

            h(cma, m)
        except Exception as e:
            errMsg = fmtExc(e, inclTraceback=srv.debug)
            srvMsg = {
                'descr': f"failed to process command `{cmd}': {errMsg}",
            }
            self.pushResponse(cma, m, srvMsg=srvMsg, status=127)

    def cmd_addAuthKey(self, cma, m):
        n = m.get('user')
        k = m.get('authKey')
        if not n: raise Exception(f'missing the argument "user"')
        if not k: raise Exception(f'missing the argument "authKey"')

        ut = srv.usersTbl
        ut.addAuthKey(n, k)

        self.pushResponse(cma, m)

    def cmd_rmAuthKey(self, cma, m):
        n = m.get('user')
        k = m.get('authKey')
        if not n: raise Exception(f'missing the argument "user"')
        if not k: raise Exception(f'missing the argument "authKey"')

        ut = srv.usersTbl
        ut.rmAuthKey(n, k)

        self.pushResponse(cma, m)

    def cmd_rmAllAuthKeys(cma, m):
        n = m.get('user')
        if not n: raise Exception(f'missing the argument "user"')

        ut = srv.usersTbl
        ut.rmAllAuthKeys(n)

        self.pushResponse(cma, m)

    def pushResponse(self, cma, m, srvMsg=None, execCliCB=True, status=0):
        cbFromCliMsg = m if m.get('callback') else None

        srvMsg = dict(srvMsg if srvMsg else {})
        srvMsg.update({
            'type': 'admin',
            'status': status,
        })
        cma.pushMessage(srvMsg, cbFromCliMsg=m, ignoreMissingCallback=True)
