from itertools import chain

from handyPyUtil.classes import ClonableClass

class BaseMessageArray(ClonableClass):
    MSG_TYPES = ('admin',)
    EDITABLE_TUPLE_ATTRS = ('MSG_TYPES',)
