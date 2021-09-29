from itertools import chain

class BaseMessageArray:
    MSG_TYPES = ('admin')

    @classmethod
    def cloneClass(Cls,
        setMsgTypes = None,
        addMsgTypes = None,
        rmMsgTypes = None,
    ):
        n = Cls.__name__
        clsCnt = []
        exec(f"""
class {n}(Cls): pass
clsCnt.append({n})
""")
        Clone = clsCnt.pop()

        nMsgTypesOpts = sum(map(lambda x: int(x is not None), (
            setMsgTypes, addMsgTypes, rmMsgTypes)
        ))

        if nMsgTypesOpts == 0:
            pass
        elif nMsgTypesOpts == 1:
            mtsAttr = f'MSG_TYPES'
            mts = None
            if setMsgTypes is not None:
                mts = setMsgTypes
            if addMsgTypes is not None:
                mts = chain(getattr(Clone, mtsAttr, ()), addMsgTypes)
            if rmMsgTypes is not None:
                rmSet = set(rmMsgTypes)
                mts = (
                    mt for mt in getattr(Clone, mtsAttr, ()) if mt not in rmSet
                )

            setattr(Clone, mtsAttr, tuple(mts))
        else: raise Exception(f'incompatible options')

        return Clone
