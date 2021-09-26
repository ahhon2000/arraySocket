import threading
import logging
from pathlib import Path
import sys

from handyPyUtil.loggers import addStdLogger
from handyPyUtil.concur import ConcurSensitiveObjs

class BaseClientServer:
    def __init__(self,
        debug = False,
        sock_kwarg = None,
        isServer = False,
        CMAClass = None, SMAClass = None,
        logger = None,
    ):
        self.debug = debug
        addStdLogger(self, default=logger, debug=debug)

        if not sock_kwarg: sock_kwarg = {}
        self.sock_kwarg = sock_kwarg

        self.isServer = isServer

        if not CMAClass:
            if isServer:
                from server import ClientMessageArray
            else:
                from client import ClientMessageArray
            CMAClass = ClientMessageArray
        if not SMAClass:
            if isServer:
                from server import ServerMessageArray
            else:
                from client import ServerMessageArray
            SMAClass = ServerMessageArray

        self.CMAClass = CMAClass
        self.SMAClass = SMAClass

        # Initialise concurrency-related objects

        self.evtStop = threading.Event()

        self.lock = lock = threading.RLock()
        self.concur = concur = ConcurSensitiveObjs(lock)
        with concur:
            concur.timers = []

    def stop(self):
        self.evtStop.set()
        if not self.isServer: self.sock.disconnect()

        concur = self.concur
        with concur:
            for t in concur.timers:
                t.cancel()

    def timer(self, sec, f, *arg, **kwarg):
        """Execute f() in a separate thread; return a threading.Timer object

        If the client is already in the stopped state the function
        execution will not be scheduled and None will be returned.

        Timers creating using this method are automatically cancelled on
        a call to the method stop()
        """

        concur = self.concur
        t = None
        with concur:
            if not self.evtStop.isSet():
                t = threading.Timer(sec, f, *arg, **kwarg)
                concur.timers.append(t)
                t.start()

        return t
