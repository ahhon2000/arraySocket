from itertools import chain

class BaseMessageArray:
    SERVER_SIDE = False

    @classmethod
    def cloneClass(Cls,
        setMsgTypes = None,
        addMsgTypes = None,
        rmMsgTypes = None,
        serverSide = False,
    ):
        n = Cls.__name__
        Clone = None
        exec(f"""
class {n}({n}): pass
Clone = {n}
""")

        Clone.SERVER_SIDE = serverSide

        nMsgTypesOpts = sum(map(lambda x: int(x is not None), (
            setMsgTypes, addMsgTypes, rmMsgTypes)
        ))

        if nMsgTypesOpts == 0:
            pass
        elif nMsgTypesOpts == 1:
            if not Clone.SERVER_SIDE: raise Exception("messages types are not class members in client-side message arrays, so can't change them")

            mtsAttr = f'MSG_TYPES_SRV'
            mts = None
            if setMsgTypes is not None:
                mts = setMsgTypes
            if addMsgTypes: is not None:
                mts = chain(getattr(Clone, mtsAttr, ()), addMsgTypes)
            if rmMsgTypes is not None:
                rmSet = set(rmMsgTypes)
                mts = (
                    mt for mt in getattr(Clone, mtsAttr, ()) if mt not in rmSet
                )

            setattr(Clone, mtsAttr, tuple(mts))
        else: raise Exception(f'incompatible options')

        return Clone
