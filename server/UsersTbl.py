from collections import namedtuple
import time

from handyPyUtil.concur import ConcurSensitiveObjs

from .. import ASUser

UserAuthStatus = namedtuple('UserAuthStatus', ('status', 'descr', 'user'))

class UsersTbl:
    def __init__(self, srv,
        staticUsers = (),
        authEveryone = False,
        authUsersInMem = False,
        idleSessionDurSec = 7 * 24 * 3600,
    ):
        self.srv = srv
        self.authUsersInMem = authUsersInMem
        self.authEveryone = authEveryone
        self.logger = srv.logger

        self.idleSessionDurSec = idleSessionDurSec

        self.concur = concur = ConcurSensitiveObjs(srv.lock)
        with concur:
            concur.authUsers = {}  # format:  sid: ASUser
            concur.authUsersExpirySec = {}  # format: sid: sec_since_the_Epoch

            # Generally, it's a bad idea to maintain a large table of users in
            # memory. The attribute `staticUsers' is meant to consist of a
            # small number of embedded users (like admin), or for tests.
            #
            # Each entry in staticUsers maps a user's name to an ASUser object.
            concur.staticUsers = {u.name: u for u in staticUsers}

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

        concur = self.concur
        with concur:
            u = concur.staticUsers.get(name)
            if not u:
                u = self.lookupUser(name=name)

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

    def manageExpiry(self, renew_sids=(), rm_sids=()):
        """Control the expiry of authUser's sessions

        Identify the sessions which have expired and remove them from the table.

        If a sequence of sids is given as renew_sids (or rm_sids) then also
        renew the sessions with those sids (or remove them from the table).

        This method should be called from:
            saveAuthUser(), lookupAuthUser(), rmAuthUser(), logoutUser()
        """

        if self.authUsersInMem:
            concur = self.concur
            with concur:
                now = time.time()
                sidsToRm = set()

                aues = concur.authUsersExpirySec
                for sid in renew_sids:
                    aues[sid] = round(now + self.idleSessionDurSec)
                for sid in rm_sids:
                    sidsToRm.add(sid)

                for sid, sec in aues.items():
                    if sec <= now:
                        sidsToRm.add(sid)

                aus = concur.authUsers
                for sid in sidsToRm:
                    aus.pop(sid, None)

    def lookupUser(self, name=None):
        "Override this method for custom user lookups. Should return an ASUser"

        return None

    def saveAuthUser(self, sid=None, user=None):
        """Save a sid-user association to an internal table (or elsewhere)

        This method is called once the user has been successfully authenticated
        to authorise further message arrays from the same socket.

        The sid-user pair will be stored in memory only if the
        authUsersInMem setting is True.

        For a custom way of handling sid-user pairs (say, with a DB),
        override this method.
        """

        u = user
        if self.authUsersInMem:
            concur = self.concur
            with concur:
                concur.authUsers[sid] = u

        self.manageExpiry(renew_sids=(sid,))

    def lookupAuthUser(self, sid=None, renewExpiryIfFound=False):
        """Search the (internal) table for an authenticated user by their sid

        Override if a different mechanism of storing sid-user pairs is used.
        """

        u = None
        if self.authUsersInMem:
            concur = self.concur
            with concur:
                u = concur.authUsers.get(sid)

        if u and renewExpiryIfFound:
            self.manageExpiry(renew_sids=(sid,))

        return u

    def rmAuthUser(self, sid=None):
        """Remove an authenticated user from the (internal) sid-user table

        Override if a different mechanism of storing sid-user pairs is used.
        """

        concur = self.concur
        with concur:
            concur.authUsers.pop(sid, None)
        self.manageExpiry(rm_sids=(sid,))

    def logoutUser(self, username=None):
        """Forget all sid's associated with a given user

        Override if a different mechanism of storing sid-user pairs is used.
        """

        name = username
        concur = self.concur
        with concur:
            aus = concur.authUsers
            rm_sids = []
            for sid, u in aus.items():
                if u.name == name:
                    rm_sids.append(sid)

            for sid in rm_sids:
                aus.pop(sid, None)

            self.manageExpiry(rm_sids=rm_sids)

    def addAuthKey(self, username=None, authKey=None, isAdmin=False,
        expiresInSec = 0,
    ):
        """Add authKey to the keys of a user

        If username doesn't match any user a new user will be added with the
        given value of the isAdmin flag.

        The argument expiresInSec has no effect in this method, however this
        feature may be implemented in subclasses.

        If expiresInSec is 0 the key never expires.
        """

        name = username
        if not name: raise Exception(f'no user name given')
        if not authKey: raise Exception(f'no authKey given')

        concur = self.concur
        with concur:
            sus = concur.staticUsers

            u = sus.get(name)
            if not u:
                u = ASUser(name=name, isAdmin=isAdmin)
                sus[name] = u

            u.authKeys.add(authKey)

    def rmAuthKey(self, username=None, authKey=None):
        """Remove authKey from a user's keys
        """

        name = username
        concur = self.concur
        with concur:
            sus = concur.staticUsers
            u = sus.get(name)
            if u:
                u.authKeys.discard(authKey)

    def rmAllAuthKeys(self, username=None):
        """Remove all keys a user currently has
        """

        name = username
        concur = self.concur
        with concur:
            sus = concur.staticUsers
            u = sus.get(name)
            if u:
                u.authKeys.clear()
                sus.pop(name, None)
