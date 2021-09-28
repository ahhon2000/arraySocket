

class ServerMessageArray:
    MSG_TYPES_SRV = ('error', 'auth',)

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

    def pushMessage(self, m):
        if not isinstance(m, dict): raise Exception('message not a dictionary')

        typ = m.get('type')
        if typ not in self.MSG_TYPES_SRV:
            raise Exception(f'unsupported message type: {typ}')

        self.messages.append(m)

    def pushErrorMessage(self, descr):
        self.pushMessage({
            'type': 'error',
            'descr': descr,
        })
