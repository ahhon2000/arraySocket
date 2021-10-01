from handyPyUtil.loggers import fmtExc
from handyPyUtil.classes import ClonableClass

class AdminInterface(ClonableClass):
    USERS_TBL_CMDS = (
        'addAuthKey', 'rmAuthKey', 'rmAllAuthKeys',
        'logoutUser',
    )
    EDITABLE_TUPLE_ATTRS = ('USERS_TBL_CMDS',)

    def __init__(self, srv=None):
        self.setSrv(srv)

    def setSrv(self, srv):
        self.srv = srv
        self.logger = srv.logger if srv else None

    def processMessage(self, cma, m):
        srv = self.srv

        try:
            cmd = m.get('command', '')
            if not cmd: raise Exception(f'no command given')

            if cmd in self.USERS_TBL_CMDS:
                n, k = m.get('user'), m.get('authKey')
                if not n: raise Exception(f'missing the argument "user"')
                arg = (n, k) if k else (n,)

                ut = srv.usersTbl
                h = getattr(ut, cmd, None)
                if not h: raise Exception(f'unimplemented admin command: {cmd}')

                h(*arg)
            else:
                h = getattr(self, f'cmd_{cmd}', None)
                if not h: raise Exception(f'unsupported admin command: {cmd}')
                h(cma, m)

            self.pushResponse(cma, m)
        except Exception as e:
            errMsg = fmtExc(e, inclTraceback=srv.debug)
            srvMsg = {
                'descr': f"failed to process command `{cmd}': {errMsg}",
            }
            self.pushResponse(cma, m, srvMsg=srvMsg, status=127)

    def pushResponse(self, cma, m, srvMsg=None, execCliCB=True, status=0):
        cbFromCliMsg = m if m.get('callback') else None

        srvMsg = dict(srvMsg if srvMsg else {})
        descr = srvMsg.get('descr', ('error' if status else 'success'))

        srvMsg.update({
            'type': 'admin',
            'status': status,
            'command': m.get('command'),
            'descr': descr,
        })
        cma.pushMessage(srvMsg, cbFromCliMsg=m, ignoreMissingCallback=True)
