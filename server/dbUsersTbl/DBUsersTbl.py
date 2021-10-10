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
        if not TableRowCls: raise Exception(f'TableRowCls undefined')
        self.dbobj = dbobj
        self.q = dbobj

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

        super().__init__(*arg, **kwarg)

    def lookupUser(self, name):
        q = self.q
        tru = self.TRUser._fromColVal(self, 'name', name)

        if tru: return tru._toASUser()
        return None

    def saveAuthUser(self, sid, u):
        q = self.q
        tru = self.TRUser._fromColVal(self, 'name', u.name)
        if not tru: raise Exception(f'user "{u.name}" does not exist')

        q(uid=tru.id, sid=sid) / """
            INSERT INTO `{self.TRAuthUser._tableName}`
            (user, sid)
            VALUES (%(uid)s, %(sid)s)
        """

    def lookupAuthUser(self, sid):
        q = self.q
        trus = q(sid=sid) / """
            SELECT u.*
            FROM
                `{self.TRUser._tableName` u,
                `{self.TRAuthUser._tableName}` au
            ON
                u.id = au.user
            WHERE
                au.sid = %(sid)s
        """
        if not trus: return None

        u = trus[0]._toASUser()
        return u

    def rmAuthUser(self, sid):
        q = self.q
        q(sid=sid) / """
            DELETE FROM `{self.TRAuthUser._tableName}`
            WHERE sid = %(sid)s
        """

    def logoutUser(self, name):
        q = self.q
        q(name=name) / """
            DELETE FROM `{self.TRAuthUser._tableName}`
            WHERE
                user = (
                    SELECT u.id FROM `{self.TRUser._tableName}` u
                    WHERE u.name = %(name)s
                )
        """

    def addAuthKey(self, name, authKey):
        q = self.q

        tru = self.TRUser._fromColVal(self, 'name', name)
        if not tru:
            tru = self.TRUser(self, name=name)
            tru._save()
        u = tru._toASUser()

        if authKey not in u.authKeys:
            q(uid, authKey=authKey) / """
                INSERT INTO `self.TRAuthKey._tableName`
                (user, authKey)
                VALUES (%(uid)s, %(authKey)s)
            """

    def rmAuthKey(self, name, authKey):
        q = self.q
        q(name=name, authKey=authKey) / """
            DELETE FROM `self.TRAuthKey._tableName`
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
        q(name=name) / """
            DELETE FROM `{self.TRAuthKey._tableName}`
            WHERE
                user = (
                    SELECT u.id FROM `{self.TRUser._tableName}` u
                    WHERE u.name = %(name)s
                )
        """
