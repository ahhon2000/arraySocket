import sys, os
from pathlib import Path
import threading
from threading import Thread
from more_itertools import first

#from handyPyUtil.tests import TestKit
from handyPyUtil.db.tests import TestKitDB
from handyPyUtil.db import Database_mysql

from ..server import Server
from ..client import Client

from .. import ASUser

DFLT_TEST_ADDR = f"127.0.0.1"
DFLT_TEST_PORT = 5492
MYSQL_CNF = Path(sys.argv[0]).absolute().parent / 'mysql.cnf'

#class TestKitAS(TestKit):
class TestKitAS(TestKitDB):
    def __init__(self,
        addr=DFLT_TEST_ADDR, port=DFLT_TEST_PORT,
        CMAClass = None, SMAClass = None,
        lock = None,
        **kwarg,
    ):
        self.addr = addr
        self.port = port
        self.CMAClass = CMAClass
        self.SMAClass = SMAClass

        if not lock: lock = threading.RLock()
        self.lock = lock

        self.activeClients = []  # each element is a tuple (thread, client)

        super().__init__(lock=lock, **kwarg)

        self.connect(DBCls=Database_mysql)

    def startServer(self,
        addr = None, port = None,
        process_kwarg = {},
        usersStorage = 'memory',
        **srvKwarg
    ):
        def srvTarget(addr, port, logger, **kwargs):
            srvKwarg.setdefault('lock', self.lock)

            srv = Server(
                logger = logger, debug = True,
                usersStorage = usersStorage,
                **srvKwarg
            )
            srv.run(addr=addr, port=port)

        addr = addr if addr else self.addr
        port = port if port else self.port

        for k in ('CMAClass', 'SMAClass',):
            v = getattr(self, k)
            srvKwarg.setdefault(k, v)

        p = self.forkProcess(srvTarget,
            args=(addr, port, self.logger), kwargs=srvKwarg,
            **process_kwarg
        )
        return p

    def startClient(self,
        addr = None, port = None,
        thread_kwarg = {},
        user = None,  # can be a username or an ASUser object
        debug = True,
        **cliKwarg
    ):
        """Initialise and start a client in a new thread; return cli, thread

        All clients started with this method will be automatically
        stopped when the `with' clause is done.
        """

        addr = addr if addr else self.addr
        port = port if port else self.port
        uri = f"http://{addr}:{port}"

        if user:
            if isinstance(user, ASUser):
                cliKwarg.update({
                    'user': user.name,
                    'authKey': first(user.authKeys),
                    'debug': debug,
                })
            else: cliKwarg['user'] = user

        cliKwarg.setdefault('lock', self.lock)
        cli = Client(uri, logger=self.logger, **cliKwarg)

        def trgCli():
            cli.run()
        thCli = Thread(target=trgCli, **thread_kwarg)
        thCli.start()

        self.activeClients.append((thCli, cli))

        return cli, thCli

    def getUri(self):
        return f"http://{self.addr}:{self.port}"

    def cleanup(self, *arg, **kwarg):
        self._cleanupClients()
        super().cleanup(*arg, **kwarg)

    def _cleanupClients(self):
        acs = self.activeClients

        for thCli, cli in acs:
            cli.stop()

        acs.clear()
