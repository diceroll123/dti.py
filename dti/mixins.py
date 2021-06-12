from typing import Union


class Object:
    __slots__ = ()
    id: Union[int, str]

    def __eq__(self, other):
        return isinstance(other, self.__class__) and other.id == self.id

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return other.id != self.id
        return True

    def __hash__(self):
        return hash(str(self.__class__) + str(self.id))
