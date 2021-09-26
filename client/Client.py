import threading
import time

import socketio
from . import ServerMessageArray, ClientMessageArray
from handyPyUtil.concur import ConcurSensitiveObjs

SOCKET_REINIT_ON_FAILURE_SEC = 10

class StopClientExc(Exception): pass

class Client:
    def __init__(self,
        uri = "http://127.0.0.1:5490",
        user = '', authKey = '',
        debug = False,
        **sock_kwarg,
    ):
        self.uri = uri
        self.user = user
        self.authKey = authKey
        self.debug = debug

        self._evtStop = threading.Event()
        self.sock = None
        self.sock_kwarg = sock_kwarg

        self.lock = lock = threading.RLock()
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

    def onDisconnect(self):
        if self._evtStop.isSet():
            raise StopClientExc(f'The client has been ordered to stop. Stopping...')
        print('disconnected')
        

    def _initSocket(self):
        self.sock = sock = socketio.Client(**self.sock_kwarg)

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
                sock = self._initSocket()
                sock.connect(self.uri)
                sock.wait()
            except StopClientExc:
                self._evtStop.set()
            except Exception as e:
                print(f'socket error: {e};\nreinitialising the socket and reconnecting')

    def stop(self):
        self._evtStop.set()
        self.sock.disconnect()
