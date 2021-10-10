from handyPyUtil.db import TableRow
from handyPyUtil.db.Database import DBTYPES

class TRAuthUser(TableRow):
    _primaryKey = 'sid'
    _columnDefs = {
        'user': {
            DBTYPES.mysql: "BIGINT UNSIGNED NOT NULL",
        },
        'sid': {
            DBTYPES.mysql: "VARCHAR(128) PRIMARY KEY NOT NULL COLLATE utf8_bin",
        },
    }

    @classmethod
    def _getDynamicConstraints(Cls):
        cs = super()._getDynamicConstraints()
        cs.update({
            DBTYPES.mysql: [
                f"""
                    CONSTRAINT `fk__auth_user` FOREIGN KEY (`user`)
                    REFERENCES `{Cls._usersTableName}`(`id`)
                    ON DELETE CASCADE
                """,
            ],
        })

        return cs
