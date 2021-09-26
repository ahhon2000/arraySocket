import threading
import time

import socketio
from BaseClientServer import BaseClientServer

DFLT_SOCK_REINIT_ON_FAILURE_SEC = 10

class Client(BaseClientServer):
    def __init__(self,
        uri = "http://127.0.0.1:5490",
        user = '', authKey = '',
        sockReinitSec = DFLT_SOCK_REINIT_ON_FAILURE_SEC,
        **kwarg,
    ):
        super().__init__(**kwarg)

        self.sockReinitSec = sockReinitSec
        self.uri = uri
        self.user = user
        self.authKey = authKey

        concur = self.concur
        with concur:
            concur.MSG_TYPES_CLI = ['auth']
            concur.MSG_TYPES_SRV = ['auth']

            concur.clientMessageArrays = {}
            concur.curCliMessageArray = None

        self.newClientMessageArray()

    def setMsgTypes(self, k, mts0):
        concur = self.concur
        with concur:
            mts = getattr(concur, k)
            mts.clear()
            mts.extend(mts0)

    def newClientMessageArray(self):
        concur = self.concur
        cma = self.CMAClass(self)
        with concur:
            concur.clientMessageArrays[cma.ref] = cma
            concur.curCliMessageArray = cma

    def login(self):
        self.pushMessage({
            'type': 'auth',
            'user': self.user,
            'authKey': self.authKey,
        })
        self.sendMessages()

    def onConnect(self):
        self.login()

    def onDisconnect(self):
        print('disconnected')
        

    def _initSocket(self):
        self.sock = sock = socketio.Client(**self.sock_kwarg)

        @sock.event
        def connect():
            self.onConnect()

        @sock.event
        def disconnect():
            self.onDisconnect()

        @sock.event
        def server_message_array(ms):
            self.onServerMessageArray(ms)

        return sock

    def onServerMessageArray(self, ms):
        try:
            sma = self.SMAClass(self, ms)
            sma.processMessages()
        except Exception as e:
            print(f'error while processing messages: {e}')

    def discardCliMessageArray(self, cma):
        concur = self.concur
        with concur:
            cmas = concur.clientMessageArrays
            cmas.pop(cma.ref, None)

    def pushMessage(self, m):
        concur = self.concur
        with concur:
            cma = concur.curCliMessageArray
            cma.pushMessage(m)

    def sendMessages(self):
        concur = self.concur
        with concur:
            cma = concur.curCliMessageArray
            cma.send()
            self.newClientMessageArray()

    def run(self):
        firstConnect = True

        while not self.evtStop.isSet():
            time.sleep(0 if firstConnect else self.sockReinitSec)
            firstConnect = False

            try:
                sock = self._initSocket()
                sock.connect(self.uri)
                sock.wait()
            except Exception as e:
                print(f'socket error: {e};\nreinitialising the socket and reconnecting')
