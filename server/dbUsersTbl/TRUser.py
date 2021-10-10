from handyPyUtil.db import TableRow
from handyPyUtil.db.Database import DBTYPES

from ... import ASUser

class TRUser(TableRow):
    _columnDefs = {
        'id': {
            DBTYPES.mysql: "INTEGER UNSIGNED PRIMARY KEY NOT NULL AUTO_INCREMENT",
        },
        'name': {
            DBTYPES.mysql: "VARCHAR(64) UNIQUE NOT NULL COLLATE utf8_bin",
        },
        'isAdmin': {
            DBTYPES.mysql: "TINYINT NOT NULL DEFAULT 0",
        },
    }

    def _toASUser(self, loadKeys=True):
        authKeys = ()
        if loadKeys:
            if not self.id: raise Exception(f'id not set')
            q = self._dbobj
            tbl = self._bindObject.authKeysTableName

            rowToKey = lambda r: r['authKey']
            authKeys = q(Id=self.id, aslist=True) / rowToKey /f"""
                SELECT `authKey` FROM `{tbl}`
                WHERE `user` = %(Id)s
            """

        u = ASUser(
            name=self.name, isAdmin=bool(self.isAdmin), authKeys=authKeys
        )

        return u
