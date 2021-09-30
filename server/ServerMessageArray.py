from .. import BaseMessageArray

class ServerMessageArray(
    BaseMessageArray.cloneClass(
        setMsgTypes = ('error', 'auth', 'admin'),
    )
):
    def __init__(self, srv, sid, messages=()):
        self.logger = srv.logger

        self.srv = srv
        self.sid = sid
        self.messages = list(messages)

    def send(self):
        ms = self.messages
        if not ms: return

        srv = self.srv
        sock = srv.sock
        sid = self.sid
        sock.emit('server_message_array', ms, room=sid)

    def pushMessage(self, m,
        cbFromCliMsg = None,
        ignoreMissingCallback = False,
    ):
        """Add a server message to the array

        Optionally, if cbFromCliMsg is given and is a client message
        order the client to execute the callback which that message must
        contain references to.
        """

        if not isinstance(m, dict): raise Exception('message not a dictionary')

        typ = m.get('type')
        if typ not in self.MSG_TYPES:
            raise Exception(f'unsupported message type: {typ}')

        m = dict(m)
        if cbFromCliMsg:
            cbk = cbFromCliMsg.get('callback')
            cmaRef = cbFromCliMsg.get('clientMessageArray')

            if cbk:
                if cmaRef:
                    m.update({
                        'callback': cbk,
                        'clientMessageArray': cmaRef,
                    })
                else: raise Exception(f'the client has scheduled a callback but has not provided cmaRef')
            else:
                if not ignoreMissingCallback:
                    raise Exception(f"could not determine the client's callback reference")

        self.messages.append(m)

    def pushErrorMessage(self, descr):
        self.pushMessage({
            'type': 'error',
            'descr': descr,
        })
