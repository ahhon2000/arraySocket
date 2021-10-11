from itertools import chain
from .. import ASUser

def spawnUsers(N, andAdmin=True, adminAuthKey='adminsecret'):
    class IASUser(ASUser):
        def __init__(self, *arg, index=None, **kwarg):
            super().__init__(*arg, **kwarg)
            self.index = index

    useq = []
    if andAdmin:
        useq.append(
            (('admin', adminAuthKey, True, None),),
        )
    useq.append(
        ((f'user{i}', '', False, i) for i in range(N)),
    )

    us = {
        n: IASUser(name=n, authKeys=(k,), isAdmin=ia, index=i)
            for n, k, ia, i in chain(*useq)
    }

    cliDicts = {
        n: {
            'user': u,
        } for n, u in us.items()
    }

    return cliDicts
