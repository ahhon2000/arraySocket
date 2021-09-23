from core.strings import genRandomStr
from core import ConcurSensitiveObjs

ACK_TIMEOUT_SEC = 10
DFLT_SEC_TO_LIVE = 60

class ClientMessageArray:
    def __init__(self, fzhc, ms=()):
        self.ref = genRandomStr()

        ms = list(ms)
        self.flazhClient = fzhc

        if not fzhc.lock: raise Exception(f'flachClient lock is undefined')
        self.concur = concur = ConcurSensitiveObjs(fzhc.lock)

        with concur:
            concur.messages = []
            concur.sent = False
            concur.processedByServer = False
            concur.timedOut = False
            concur.expired = False
            concur.secToLive = DFLT_SEC_TO_LIVE
            concur.callbacks = {}

            for m in ms:
                self.pushMessages(m)

    def pushMessage(self, m):
        """If m.responseValidForSec is given
        (and is greater than other messages', or the default value)
        it sets for how many seconds to keep this ClientMessageArray after
        it is sent to the server.
        
        If a function is provided as m.callback it will be kept in this
        object until it times out/expires, so that the server can trigger
        it, if necessary.
        """

        fzhc = self.fzhc
        concur = self.concur

        with concur:
            if self.sent: raise Exception('cannot add a message to an array that has already been sent')

            typ = m.get('type')
            if typ is None: raise Exception(f'a client message is missing the type attribute')

            if typ not in fzhc.concur.MSG_TYPES_CLI: raise Exception(f'unsupported client message type: {typ}')

            m = dict(m)
            m.clientMessageArray = self.ref

            vsec = m.get('responseValidForSec')
            if vsec and vsec > concur.secToLive:
                concur.secToLive = vsec

            cb = m.get('callback')
            if cb:
                cbk = genRandomStr()
                concur.callbacks[cbk] = cb
                m['callback'] = cbk

            self.messages.push(m)

    def onStatusChange(ack=False, data=None, timedOut=False, expired=False):
        fzhc = self.fzhc
        # TODO complete
