from collections import namedtuple

from .. import ASUser

UserAuthStatus = namedtuple('UserAuthStatus', ('status', 'descr', 'user'))

class UsersTbl:
    def __init__(self,
        staticUsers = (),
        authEveryone = False,
        authUsersInMem = False,
    ):
        self.authUsersInMem = authUsersInMem
        self._authUsers = {}  # format:  sid: ASUser

        # Generally, it's a bad idea to maintain a large table of users in
        # memory. The attribute `staticUsers' is meant to consist of a
        # small number of embedded users (like admin), or for tests.
        #
        # Each entry in staticUsers maps a user's name to an ASUser object.
        self.staticUsers = {u.name: u for u in staticUsers}

        self.authEveryone = authEveryone
        self.authUsersInMem = authUsersInMem

    def checkUserCredentials(self, name, authKey):
        """Check if a user is allowed to access the server

        NOTE: For custom user lookups (e. g. in a DB) override
        lookupUser() instead of this function

        Return value: a named tuple (status, descr, user)

        status is 0 iff access is granted
        descr is a short description of the status.
        user is the user object
        """

        S = UserAuthStatus
        s = S(127, 'unknown authentication error', None)

        u = self.staticUsers.get(name)
        if not u:
            u = self.lookupUser(name)

        if self.authEveryone:
            s = S(0, 'success', u)
        elif not name:
            s = S(1, 'no user', u)
        else:
            if not authKey:
                s = S(2, 'no authentication key', u)
            else:
                s = S(3, 'wrong credentials', u)
                if u:
                    if name == u.name  and  authKey in u.authKeys:
                        s = S(0, 'success', u)

        return s

    def lookupUser(self, name):
        "Override this method for custom user lookups. Should return an ASUser"

        return None

    def saveAuthUser(self, sid, u):
        """Save a sid-user association to an internal table (or elsewhere)

        This method is called once the user has been successfully authenticated
        to authorise further message arrays from the same socket.

        The sid-user pair will be stored in memory only if the
        authUsersInMem setting is True.

        For a custom way of handling sid-user pairs (say, with a DB),
        override this method.
        """

        if self.authUsersInMem:
            self._authUsers[sid] = u

    def lookupAuthUser(self, sid):
        """Search the (internal) table for an authenticated user by their sid

        Override if a different mechanism of storing sid-user pairs is used.
        """

        u = None
        if self.authUsersInMem:
            u = self._authUsers.get(sid)

        return u

    def rmAuthUser(self, sid):
        """Remove an authenticated user from the (internal) sid-user table

        Override if a different mechanism of storing sid-user pairs is used.
        """

        self._authUsers.pop(sid, None)

    def addAuthKey(self, name, authKey):
        """Add authKey to the keys of a users
        """

        if not name: raise Exception(f'no user name given')
        if not authKey: raise Exception(f'no authKey given')

        sus = self.staticUsers

        u = sus.get(name)
        if not u:
            u = ASUser(name=name)
            sus[name] = u

        u.authKeys.add(authKey)

    def rmAuthKey(self, name, authKey):
        """Remove authKey from a user's keys
        """

        sus = self.staticUsers
        u = sus.get(name)
        if u:
            u.authKeys.discard(authKey)

    def rmAllAuthKeys(self, name):
        """Remove all keys a user currently has
        """

        sus = self.staticUsers
        u = sus.get(name)
        if u:
            u.authKeys.clear()
            sus.pop(name, None)
