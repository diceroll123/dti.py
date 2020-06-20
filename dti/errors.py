class DTIException(Exception):
    """Base exception class for dti.py"""

    pass


class NeopetNotFound(DTIException):
    """An exception that is thrown when searching a neopet by name returns nothing"""

    pass


class MissingPetAppearance(DTIException):
    """An exception that is thrown when a pet appearance does not exist"""

    pass


class InvalidColorSpeciesPair(DTIException):
    """An exception that is thrown when trying to create an invalid Color/Species pair"""

    pass


class InvalidPairBytes(DTIException):
    """An exception that is thrown when the valid pet poses table data does not match. This means DTI has changed how the bit table is set up."""

    pass


class NoIteratorsFound(DTIException):
    """An exception that is thrown when search parameters are unable to form a proper search query"""

    pass


class BrokenAssetImage(DTIException):
    """An exception that is thrown when the biology/object image is broken and must be reported to fix."""

    pass
