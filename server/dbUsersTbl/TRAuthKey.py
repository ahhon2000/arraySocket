from handyPyUtil.db import TableRow
from handyPyUtil.db.Database import DBTYPES

class TRAuthKey(TableRow):
    _primaryKey = 'authKey'
    _columnDefs = {
        'id': {
            DBTYPES.mysql: "BIGINT UNSIGNED PRIMARY KEY NOT NULL AUTO_INCREMENT",
        },
        'user': {
            DBTYPES.mysql: "BIGINT UNSIGNED NOT NULL",
        },
        'authKey': {
            DBTYPES.mysql: "VARCHAR(64) NOT NULL COLLATE utf8_bin",
        },
    }

    @classmethod
    def _getDynamicConstraints(Cls):
        cs = super()._getDynamicConstraints()
        cs.update({
            DBTYPES.mysql: [
                f"""
                    CONSTRAINT `fk_auth_key` FOREIGN KEY (`user`)
                    REFERENCES `{Cls._usersTableName}`(`id`)
                    ON DELETE CASCADE
                """,
            ],
        })

        return cs
