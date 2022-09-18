class DTIException(Exception):
    """Base exception class for dti.py"""

    pass


class NeopetNotFound(DTIException):
    """An exception that is thrown when searching a neopet by name returns nothing"""

    pass


class GlitchedNeopet(DTIException):
    """An exception that is thrown when a glitched neopet is requested, such as an Asparagus Hissi."""

    # ideally we will never have an actual Asparagus Hissi, but this is a good example of a glitched neopet

    pass


class MissingModelData(DTIException):
    """An exception that is thrown when a pet's data isn't in DTI's database yet."""

    pass


class OutfitNotFound(DTIException):
    """An exception that is thrown when searching a DTI outfit by ID returns nothing"""

    pass


class MissingPetAppearance(DTIException):
    """An exception that is thrown when a pet appearance (species + color + pose) does not exist"""

    pass


class InvalidColor(DTIException):
    """An exception that is thrown when an invalid color is passed into the color cache."""

    pass


class InvalidSpecies(DTIException):
    """An exception that is thrown when an invalid species is passed into the species cache."""

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


class NullAssetImage(DTIException):
    """An exception that is thrown when the biology/object image is null and must be reported to fix. Alternatively, the item does not have a PNG/SVG appearance, and only a Movie appearance."""

    pass


class InvalidItemID(DTIException):
    """An exception that is thrown when an invalid item ID is searched. The whole search query fails."""

    pass


class HTTPException(DTIException):
    """An exception that is thrown when an HTTP request operation fails."""

    pass
