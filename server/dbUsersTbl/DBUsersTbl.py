from .. import UsersTbl

class DBUsersTbl(UsersTbl):
    def __init__(self, *arg,
        dbobj=None,
        usersTableName = 'array_server_users',
        authUsersTableName = 'array_server_auth_users',
        authKeysTableName = 'array_server_auth_keys',
        **kwarg
    ):
        # TODO devise a mechanism to logout users who have not
        # TODO sent a message in a specified interval

        if not dbobj: raise Exception(f'dbobj undefined')
        self.dbobj = dbobj
        self.q = dbobj
        super().__init__(*arg, **kwarg)

        self.logger.debug(f'initialising DBUsersTbl')

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

    def lookupUser(self, name):
        q = self.q
        tru = self.TRUser._fromColVal(self, 'name', name)

        if tru: return tru._toASUser()
        return None

    def saveAuthUser(self, sid, u):
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

    def lookupAuthUser(self, sid):
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

        u = trus[0]._toASUser()
        return u

    def rmAuthUser(self, sid):
        q = self.q
        q(sid=sid) / f"""
            DELETE FROM `{self.TRAuthUser._tableName}`
            WHERE sid = %(sid)s
        """

    def logoutUser(self, name):
        q = self.q
        q(name=name) / f"""
            DELETE FROM `{self.TRAuthUser._tableName}`
            WHERE
                user = (
                    SELECT u.id FROM `{self.TRUser._tableName}` u
                    WHERE u.name = %(name)s
                )
        """

    def addAuthKey(self, name, authKey, isAdmin=False):
        q = self.q

        tru = self.TRUser._fromColVal(self, 'name', name)
        if not tru:
            tru = self.TRUser(self, name=name, isAdmin=isAdmin)
            tru._save()
        u = tru._toASUser()

        if authKey not in u.authKeys:
            uid = tru.id
            if not uid: raise Exception(f'uid undefined')
            q(uid=uid, authKey=authKey) / f"""
                INSERT INTO `{self.TRAuthKey._tableName}`
                (user, authKey)
                VALUES (%(uid)s, %(authKey)s)
            """

    def rmAuthKey(self, name, authKey):
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

    def rmAllAuthKeys(self, name):
        q = self.q
        q(name=name) / f"""
            DELETE FROM `{self.TRAuthKey._tableName}`
            WHERE
                user = (
                    SELECT u.id FROM `{self.TRUser._tableName}` u
                    WHERE u.name = %(name)s
                )
        """
