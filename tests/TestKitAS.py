from handyPyUtil.tests import TestKit
from server import Server

DFLT_TEST_PORT = 5492
DFLT_TEST_ADDR = f"127.0.0.1"

class TestKitAS(TestKit):
    def __init__(self,
        addr=DFLT_TEST_ADDR, port=DFLT_TEST_PORT,
        CMAClass = None, SMAClass = None,
        *arg, **kwarg
    ):
        self.addr = addr
        self.port = port
        self.CMAClass = CMAClass
        self.SMAClass = SMAClass
        super().__init__(*arg, **kwarg)

    def startServer(self,
        addr = None, port = None,
        process_kwarg = {},
        **srvKwarg
    ):
        def srvTarget(addr, port, **kwargs):
            srv = Server(**srvKwarg)
            srv.run(addr=addr, port=port)

        addr = addr if addr else self.addr
        port = port if port else self.port

        for k in ('CMAClass', 'SMAClass',):
            v = getattr(self, k)
            srvKwarg.setdefault(k, v)

        p = self.forkProcess(srvTarget,
            args=(addr, port), kwargs=srvKwarg,
            **process_kwarg
        )
        return p

    def getUri(self):
        return f"http://{self.addr}:{self.port}"
