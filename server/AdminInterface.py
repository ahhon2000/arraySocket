from handyPyUtil.loggers import fmtExc
from handyPyUtil.classes import ClonableClass

class AdminInterface(ClonableClass):
    USERS_TBL_CMDS = {
        'addAuthKey': {'args': ('user', 'authKey',)},
        'rmAuthKey': {'args': ('user', 'authKey',)},
        'rmAllAuthKeys': {'args': ('user',)},
        'logoutUser': {'args': ('user',)},
    }

    def __init__(self, srv):
        self.srv = srv
        self.logger = srv.logger

    def processMessage(self, cma, m):
        srv = self.srv

        try:
            cmd = m.get('command', '')
            if not cmd: raise Exception(f'no command given')

            if cmd in self.USERS_TBL_CMDS:
                argNames = self.USERS_TBL_CMDS[cmd]['args']
                arg = []
                for an in argNames:
                    av = m.get(an)
                    if an is None: raise Exception(f'missing argument "{an}"')
                    arg.append(av)

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
