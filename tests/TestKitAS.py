from handyPyUtil.tests import TestKit
from server import Server

DFLT_TEST_PORT = 5492

class TestKitAS(TestKit):
    def __init__(self, *arg, **kwarg):
        super().__init__(*arg, **kwarg)

    def startServer(self, port=DFLT_TEST_PORT, **pkwarg):
        def srvTarget(**kwargs):
            srv = Server()
            srv.run(addr="127.0.0.1", port=kwargs['port'])

        srvKwarg = {
            'port': port,
        }

        p = self.forkProcess(srvTarget, args=(), kwargs=srvKwarg, **pkwarg)
        return p
