
MSG_TYPES_SRV = ('error', 'auth',)

class ServerMessageArray:
    def __init__(self, fzhs, sid, messages=()):
        self.sid = sid
        self.flazhServer = fzhs
        self.messages = list(messages)

    def send(self):
        ms = self.messages
        if not ms: return

        fzhs = self.flazhServer
        sock = fzhs.sock
        sid = self.sid
        sock.emit('server_message_array', ms, room=sid)

    def pushMessage(self, m):
        if not isinstance(m, dict): raise Exception('message not a dictionary')

        typ = m.get('type')
        if typ not in MSG_TYPES_SRV:
            raise Exception(f'unsupported message type: {typ}')

        self.messages.append(m)

    def pushErrorMessage(self, descr):
        self.pushMessage({
            'type': 'error',
            'descr': descr,
        })
