from itertools import chain

from handyPyUtil.classes import ClonableClass

class BaseMessageArray(ClonableClass):
    MSG_TYPES = ('admin',)

    @classmethod
    def cloneClass(Cls, **kwarg):
        eta = ('MSG_TYPES',)
        Clone = super().cloneClass(editableTupleAttrs=eta, **kwarg)

        return Clone
