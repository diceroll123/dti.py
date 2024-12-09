class Object:
    __slots__ = ()
    id: int

    def __eq__(self, other: object) -> bool:
        return isinstance(other, self.__class__) and other.id == self.id

    def __ne__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return other.id != self.id
        return True

    def __hash__(self) -> int:
        return hash(str(self.__class__) + str(self.id))
