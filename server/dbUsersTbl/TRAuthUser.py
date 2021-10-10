from handyPyUtil.db import TableRow
from handyPyUtil.db.Database import DBTYPES

class TRAuthUser(TableRow):
    _primaryKey = 'sid'
    _columnDefs = {
        'user': {
            DBTYPES.mysql: "INTEGER UNSIGNED NOT NULL",
        },
        'sid': {
            DBTYPES.mysql: "VARCHAR(128) PRIMARY KEY NOT NULL COLLATE utf8_bin",
        },
    }

    def _getDynamicConstraints(self):
        cs = super()._getDynamicConstraints()
        cs.update({
            DBTYPES.mysql: [
                f"""
                    CONSTRAINT `fk_user` FOREIGN KEY (`user`)
                    REFERENCES `{self._usersTableName}`(`id`)
                    ON DELETE CASCADE
                """,
            ],
        })

        return cs
