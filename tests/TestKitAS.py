from threading import Thread

from handyPyUtil.tests import TestKit
from ..server import Server
from ..client import Client

from .. import ASUser

DFLT_TEST_ADDR = f"127.0.0.1"
DFLT_TEST_PORT = 5492

class TestKitAS(TestKit):
    def __init__(self,
        addr=DFLT_TEST_ADDR, port=DFLT_TEST_PORT,
        CMAClass = None, SMAClass = None,
        **kwarg,
    ):
        self.addr = addr
        self.port = port
        self.CMAClass = CMAClass
        self.SMAClass = SMAClass

        self.activeClients = []  # each element is a tuple (thread, client)

        super().__init__(**kwarg)

    def startServer(self,
        addr = None, port = None,
        process_kwarg = {},
        **srvKwarg
    ):
        def srvTarget(addr, port, logger, **kwargs):
            srv = Server(logger=logger, debug=True, **srvKwarg)
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
                cliKwarg.update({'user': user.name, 'authKey': user.authKey})
            else: cliKwarg['user'] = user

        cli = Client(uri, logger=self.logger, **cliKwarg)

        def trgCli():
            cli.run()
        thCli = Thread(target=trgCli, **thread_kwarg)
        thCli.start()

        self.activeClients.append((thCli, cli))

        return cli, thCli

    def getUri(self):
        return f"http://{self.addr}:{self.port}"

    def cleanup(self, **kwarg):
        self._cleanupClients()
        super().cleanup()

    def _cleanupClients(self):
        acs = self.activeClients

        for thCli, cli in acs:
            cli.stop()

        acs.clear()
