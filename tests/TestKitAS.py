from handyPyUtil.tests import TestKit
from server import Server

DFLT_TEST_PORT = 5492
DFLT_TEST_ADDR = f"127.0.0.1"

class TestKitAS(TestKit):
    def __init__(self, addr=DFLT_TEST_ADDR, port=DFLT_TEST_PORT, *arg, **kwarg):
        self.addr = addr
        self.port = port
        super().__init__(*arg, **kwarg)

    def startServer(self, **pkwarg):
        def srvTarget(**kwargs):
            srv = Server()
            srv.run(addr=kwargs['addr'], port=kwargs['port'])

        srvKwarg = {
            'addr': self.addr,
            'port': self.port,
        }

        p = self.forkProcess(srvTarget, args=(), kwargs=srvKwarg, **pkwarg)
        return p

    def getUri(self):
        return f"http://{self.addr}:{self.port}"
