from threading import Timer

from handyPyUtil.strings import genRandomStr
from handyPyUtil.concur import ConcurSensitiveObjs

ACK_TIMEOUT_SEC = 10
DFLT_SEC_TO_LIVE = 60
RANDOM_REFS_LEN = 24

class ClientMessageArray:
    def __init__(self, cli, ms=()):
        self.logger = cli.logger
        self.ref = genRandomStr(RANDOM_REFS_LEN)

        ms = list(ms)
        self.cli = cli

        if not cli.lock: raise Exception(f'flachClient lock is undefined')
        self.concur = concur = ConcurSensitiveObjs(cli.lock)

        with concur:
            concur.messages = []
            concur.sent = False
            concur.processedByServer = False
            concur.timedOut = False
            concur.expired = False
            concur.secToLive = DFLT_SEC_TO_LIVE
            concur.callbacks = {}

            for m in ms:
                self.pushMessage(m)

    def pushMessage(self, m):
        """If m.responseValidForSec is given
        (and is greater than other messages', or the default value)
        it sets for how many seconds to keep this ClientMessageArray after
        it is sent to the server.
        
        If a function is provided as m.callback it will be kept in this
        object until it times out/expires, so that the server can trigger
        it, if necessary.
        """

        cli = self.cli
        concur = self.concur

        with concur:
            if self.concur.sent: raise Exception('cannot add a message to an array that has already been sent')

            typ = m.get('type')
            if typ is None: raise Exception(f'a client message is missing the type attribute')

            if typ not in cli.concur.MSG_TYPES_CLI: raise Exception(f'unsupported client message type: {typ}')

            m = dict(m)
            m['clientMessageArray'] = self.ref

            vsec = m.get('responseValidForSec')
            if vsec and vsec > concur.secToLive:
                concur.secToLive = vsec

            cb = m.get('callback')
            if cb:
                cbk = genRandomStr(RANDOM_REFS_LEN)
                concur.callbacks[cbk] = cb
                m['callback'] = cbk
                self.logger.debug(f'added a callback to the client ClientMessageArray')

            concur.messages.append(m)

    def onStatusChange(self,
        ack=False, data=None, timedOut=False, expired=False
    ):
        cli = self.cli
        concur = self.concur

        if ack and timedOut: raise Exception(f'ack & timedOut cannot be used together')
        if ack and expired: raise Exception(f'ack & expired cannot be used together')

        with concur:
            if ack:
                concur.processedByServer = True
                self.logger.debug(f'server has processed messages: {data}')

            if timedOut:
                concur.timedOut = True
                self.logger.warning('server acknowledgement timed out')

            if expired:
                concur.expired = True

            if concur.timedOut or concur.expired or \
                concur.processedByServer and not self.callbacksPending():

                cli.discardCliMessageArray(self)

    def callbacksPending(self):
        concur = self.concur
        ret = False
        with concur:
            ret = bool(concur.callbacks)

        return ret

    def send(self):
        cli = self.cli
        sock = cli.sock
        concur = self.concur
        ms = concur.messages

        with concur:
            if concur.sent: raise Exception('the client message array has already been sent')

            if ms:
                def cb(data):
                    self.onStatusChange(ack=True, data=data)
                sock.emit('client_message_array', ms, callback=cb)

                def tf(cma):
                    if not cma.concur.processedByServer:
                        cma.onStatusChange(timedOut=True)
                cli.timer(ACK_TIMEOUT_SEC, tf, args=(self,))

            def tf(cma):
                cma.onStatusChange(expired=True)
            cli.timer(concur.secToLive, tf, args=(self,))

            concur.sent = True
            self.logger.debug(f'{len(ms)} messages sent to the server')

    def execCallback(self, cbk, m):
        concur = self.concur
        with concur:
            cb = concur.callbacks.pop(cbk, None)
            if not cb: raise Exception('the callback requested by the server is unavailable')
            cb(m)
            self.onStatusChange()
