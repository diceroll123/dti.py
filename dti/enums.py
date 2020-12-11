import random
from enum import Enum, auto

__all__ = ["LayerImageSize", "PetPose"]


class _DTIEnum(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    @classmethod
    def _missing_(cls, value):
        return cls[value]

    def __str__(self):
        return self.name

    def __int__(self):
        return int(self.value)


class LayerImageSize(_DTIEnum):
    """Represents the desired render size of a customization, in pixels.
    """

    SIZE_600 = auto()
    SIZE_300 = auto()
    SIZE_150 = auto()


class PetPose(int, _DTIEnum):
    """Represents a single pet pose. Each pose has an associated power-of-two value to easily
    create :class:`BitField` objects. This object acts like an :class:`int`.
    """

    HAPPY_MASC = 1
    SAD_MASC = 2
    SICK_MASC = 4
    HAPPY_FEM = 8
    SAD_FEM = 16
    SICK_FEM = 32
    UNCONVERTED = 64
    UNKNOWN = 128

    @classmethod
    def ideal(cls):
        return random.choice([cls.HAPPY_FEM, cls.HAPPY_MASC])

    @classmethod
    def all_fem(cls):
        return cls.SICK_FEM | cls.SAD_FEM | cls.HAPPY_FEM

    @classmethod
    def all_masc(cls):
        return cls.SICK_MASC | cls.SAD_MASC | cls.HAPPY_MASC
