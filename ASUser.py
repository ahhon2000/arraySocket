class ASUser:
    def __init__(self, name='', authKeys=(), isAdmin=False):
        self.name = name
        self.authKeys = set(authKeys)
        self.isAdmin = isAdmin
