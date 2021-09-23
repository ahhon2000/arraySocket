import threading
import time

import socketio
from . import ServerMessageArray, ClientMessageArray
from core import ConcurSensitiveObjs

SOCKET_REINIT_ON_FAILURE_SEC = 10

class FlazhClient:
    def __init__(self, uri="http://127.0.0.1:5490", **sock_kwarg):
        self.uri = uri
        self._evtStop = threading.Event()
        self.sock = None

        self.lock = threading.RLock()
        self.concur = concur = ConcurSensitiveObjs(lock)

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
        cma = ClientMessageArray(self)
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

    def onReconnect(self):
        self.login()

    def onDisconnect():
        print('disconnected')
        

    def _initSocket(self):
        self.sock = sock = socketio.Client()

        @sock.event
        def connect():
            self.onReconnect()

        @sock.event
        def disconnect():
            self.onDisconnect()

        @sock.event
        def server_message_array(ms):
            onServerMessageArray(ms)

        return sock

    def onServerMessageArray(self, ms):
        try:
            sma = ServerMessageArray(self, ms)
            sma.processMessages()
        except Exception as e:
            print(f'error while processing messages: {e}')

    def discardCliMessageArray(self, cma):
        concur = self.concur
        with concur:
            cmas = concur.clientMessageArrays
            cmas.pop(cma.get('ref'), None)

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

        while not self._evtStop.isSet():
            time.sleep(0 if firstConnect else SOCKET_REINIT_ON_FAILURE_SEC)
            firstConnect = False

            try:
                sock = self._initSocket(**sock_kwarg)
                sock.connect(self.uri)
                sock.wait()
            except Exception as e:
                print(f'socket error: {e}')

    def stop(self):
        self._evtStop.set()
