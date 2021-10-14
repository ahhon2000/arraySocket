import time

from handyPyUtil.db import Database_mysql

from .. import UsersTbl

class DBUsersTbl(UsersTbl):
    "A table of Array Socket Server users that is stored in a database"

    DFLT_DB_CLASS = Database_mysql

    def __init__(self, *arg,
        dbobj = None,
        db_kwarg = {},
        usersTableName = 'array_server_users',
        authUsersTableName = 'array_server_auth_users',
        authKeysTableName = 'array_server_auth_keys',
        secBtwExpiryCleanups = 60,
        **kwarg
    ):
        """Initialise an DBUsersTbl instance

        If dbobj is given use that database. Otherwise instantiate a new
        DFLT_DB_CLASS object. In the latter case, db_kwarg is passed on as
        keyword arguments to the DFLT_DB_CLASS constructor.
        """

        super().__init__(*arg, **kwarg)

        self.logger.debug(f'initialising DBUsersTbl')

        if not dbobj:
            dbobj = self.DFLT_DB_CLASS(**db_kwarg)

        self.dbobj = dbobj
        self.q = dbobj

        if secBtwExpiryCleanups <= 0: raise Exception(f'illegal values of secBtwExpiryCleanups')
        self.secBtwExpiryCleanups = secBtwExpiryCleanups
        self._secLastExpiryCleanup = 0

        from . import TRUser, TRAuthKey, TRAuthUser

        class TRUser(TRUser):
            _tableName = usersTableName
        self.TRUser = TRUser

        class TRAuthKey(TRAuthKey):
            _tableName = authKeysTableName
            _usersTableName = usersTableName # necessary for dynamic constraints
        self.TRAuthKey = TRAuthKey

        class TRAuthUser(TRAuthUser):
            _tableName = authUsersTableName
            _usersTableName = usersTableName # necessary for dynamic constraints
        self.TRAuthUser = TRAuthUser

        for Cls in (TRUser, TRAuthKey, TRAuthUser):
            dbobj.createTable(Cls)

    def manageExpiry(self, renew_sids=(), rm_sids=()):
        """Control the expiry of authUser's sessions

        Unlike in the base class, this method cleans up old sessions no more
        frequently than once in secBtwExpiryCleanups seconds in order to
        reduce the number of DB writing operations.

        Options renew_sids and rm_sids have immediate effect.
        """

        now = time.time()
        q = self.q

        for sid in renew_sids:
            expirySec = round(now + self.idleSessionDurSec)
            q(sid=sid, expirySec=expirySec) / f"""
                UPDATE `{self.TRAuthUser._tableName}`
                SET
                    expirySec = %(expirySec)s
                WHERE
                    sid = %(sid)s
            """

        if rm_sids:
            q(rm_sids=rm_sids) / f"""
                DELETE FROM `{self.TRAuthUser._tableName}`
                WHERE
                    sid in %(rm_sids)s
            """

        if now - self._secLastExpiryCleanup >= self.secBtwExpiryCleanups:
            self._secLastExpiryCleanup = now

            q(now=now) / f"""
                DELETE FROM `{self.TRAuthUser._tableName}`
                WHERE
                    expirySec <= %(now)s
            """


    def lookupUser(self, name=None):
        q = self.q
        tru = self.TRUser._fromColVal(self, 'name', name)

        if tru: return tru._toASUser()
        return None

    def saveAuthUser(self, sid=None, user=None):
        u = user
        q = self.q
        tru = self.TRUser._fromColVal(self, 'name', u.name)
        if not tru: raise Exception(f'user "{u.name}" does not exist')

        sids = q(sid=sid, aslist=True) / f"""
            SELECT au.sid FROM `{self.TRAuthUser._tableName}` au
            WHERE au.sid = %(sid)s
        """

        if not sids:
            q(uid=tru.id, sid=sid) / f"""
                INSERT INTO `{self.TRAuthUser._tableName}`
                (user, sid)
                VALUES (%(uid)s, %(sid)s)
            """

        self.manageExpiry(renew_sids=(sid,))

    def lookupAuthUser(self, sid=None, renewExpiryIfFound=False):
        q = self.q
        trus = q(aslist=True, sid=sid, bindObject=self) / self.TRUser / f"""
            SELECT u.*
            FROM
                `{self.TRUser._tableName}` u
                INNER JOIN
                `{self.TRAuthUser._tableName}` au
            ON
                u.id = au.user
            WHERE
                au.sid = %(sid)s
            LIMIT 1
        """
        if not trus: return None

        if renewExpiryIfFound:
            self.manageExpiry(renew_sids=(sid,))

        u = trus[0]._toASUser()
        return u

    def rmAuthUser(self, sid=None):
        q = self.q
        q(sid=sid) / f"""
            DELETE FROM `{self.TRAuthUser._tableName}`
            WHERE sid = %(sid)s
        """

        self.manageExpiry()

    def logoutUser(self, username=None):
        name = username
        q = self.q
        q(name=name) / f"""
            DELETE FROM `{self.TRAuthUser._tableName}`
            WHERE
                user = (
                    SELECT u.id FROM `{self.TRUser._tableName}` u
                    WHERE u.name = %(name)s
                )
        """

        self.manageExpiry()

    def addAuthKey(self, username=None, authKey=None, isAdmin=False,
        expiresInSec = 60,
    ):
        """

        If expiresInSec is 0 the key never expires
        """

        name = username
        q = self.q

        tru = self.TRUser._fromColVal(self, 'name', name)
        if not tru:
            tru = self.TRUser(self, name=name, isAdmin=isAdmin)
            tru._save()
        u = tru._toASUser()

        now = time.time()
        if authKey not in u.authKeys:
            uid = tru.id
            if not uid: raise Exception(f'uid undefined')
            expirySec = now + expiresInSec if expiresInSec != 0 else 0
            q(uid=uid, authKey=authKey, expirySec=round(expirySec)) / f"""
                INSERT INTO `{self.TRAuthKey._tableName}`
                (user, authKey, expirySec)
                VALUES (%(uid)s, %(authKey)s, %(expirySec)s)
            """

        q(now=round(now)) / f"""
            DELETE FROM `{self.TRAuthKey._tableName}`
            WHERE expirySec and expirySec <= %(now)s
        """

    def rmAuthKey(self, username=None, authKey=None):
        name = username
        q = self.q
        q(name=name, authKey=authKey) / f"""
            DELETE FROM `{self.TRAuthKey._tableName}`
            WHERE
                user = (
                    SELECT u.id FROM `{self.TRUser._tableName}` u
                    WHERE u.name = %(name)s
                )
                and
                authKey = %(authKey)s
        """

    def rmAllAuthKeys(self, username=None):
        name = username
        q = self.q
        q(name=name) / f"""
            DELETE FROM `{self.TRAuthKey._tableName}`
            WHERE
                user = (
                    SELECT u.id FROM `{self.TRUser._tableName}` u
                    WHERE u.name = %(name)s
                )
        """
