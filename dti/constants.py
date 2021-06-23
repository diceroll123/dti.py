from .enums import PetPose

__all__ = ("CLOSEST_POSES_IN_ORDER",)

# fragments
FRAGMENT_ITEM_PROPERTIES = """
fragment ItemProperties on Item {
  id
  name
  description
  thumbnailUrl
  rarityIndex
  isNc
  isPb
  wakaValueText
}"""

FRAGMENT_USER_PROPERTIES = """
fragment UserProperties on User {
  id
  username
}"""

FRAGMENT_PET_APPEARANCE = """
fragment PetAppearanceForOutfitPreview on PetAppearance {
  id
  pose
  bodyId
  isGlitched
  color {
    id
    name
  }
  species {
    id
    name
  }
  restrictedZones {
    id
    depth
    label
  }
  layers {
    id
    remoteId
    imageUrl(size: $size)
    knownGlitches
    zone {
      id
      depth
      label
    }
  }
}"""

FRAGMENT_ITEM_APPEARANCE = """
fragment ItemAppearanceForOutfitPreview on ItemAppearance {
  id
  restrictedZones {
    id
    depth
    label
  }
  layers {
    id
    remoteId
    imageUrl(size: $size)
    knownGlitches
    zone {
      id
      depth
      label
    }
  }
}"""


# cache species/colors
ALL_SPECIES_AND_COLORS = """
{
  allSpecies {
    id
    name
  }
  allColors {
    id
    name
  }
}"""

# search
SEARCH_ITEM_IDS = (
    """
query($itemIds: [ID!]!) {
  items(ids: $itemIds) {
    ...ItemProperties
  }
}"""
    + FRAGMENT_ITEM_PROPERTIES
)

SEARCH_TO_FIT = (
    """
query($query: String!, $fitsPet: FitsPetSearchFilter!, $speciesId: ID!, $colorId: ID!, $itemKind: ItemKindSearchFilter, $offset: Int, $limit: Int, $size: LayerImageSize!) {
  itemSearch(query: $query, fitsPet: $fitsPet, itemKind: $itemKind, offset: $offset, limit: $limit) {
    items {
      ...ItemProperties
      appearanceOn(speciesId: $speciesId, colorId: $colorId) {
        ...ItemAppearanceForOutfitPreview
      } 
    }
  }
}"""
    + FRAGMENT_ITEM_APPEARANCE
    + FRAGMENT_ITEM_PROPERTIES
)

SEARCH_QUERY = (
    """
query($query: String!, $itemKind: ItemKindSearchFilter) {
  itemSearch(query: $query, itemKind: $itemKind) {
    items {
      ...ItemProperties
    }
  }
}"""
    + FRAGMENT_ITEM_PROPERTIES
)

SEARCH_QUERY_EXACT_MULTIPLE = (
    """
query($names: [String!]!) {
  itemsByName(names: $names) {
    ...ItemProperties
  }
}"""
    + FRAGMENT_ITEM_PROPERTIES
)

SEARCH_QUERY_EXACT_SINGLE = (
    """
query($name: String!) {
  itemByName(name: $name) {
    ...ItemProperties
  }
}"""
    + FRAGMENT_ITEM_PROPERTIES
)

# grab pet appearances
GRAB_PET_APPEARANCES_WITH_ITEMS_BY_IDS = (
    """
query ($allItemIds: [ID!]!, $speciesId: ID!, $colorId: ID!, $size: LayerImageSize!) {
  petAppearances(speciesId: $speciesId, colorId: $colorId) {
    ...PetAppearanceForOutfitPreview
  }
  items(ids: $allItemIds) {
    ...ItemProperties
    appearanceOn(speciesId: $speciesId, colorId: $colorId) {
      ...ItemAppearanceForOutfitPreview
    }
  }
}"""
    + FRAGMENT_ITEM_APPEARANCE
    + FRAGMENT_ITEM_PROPERTIES
    + FRAGMENT_PET_APPEARANCE
)

GRAB_PET_APPEARANCES_WITH_ITEMS_BY_NAMES = (
    """
query ($names: [String!]!, $speciesId: ID!, $colorId: ID!, $size: LayerImageSize!) {
  petAppearances(speciesId: $speciesId, colorId: $colorId) {
    ...PetAppearanceForOutfitPreview
  }
  itemsByName(names: $names) {
    ...ItemProperties
    appearanceOn(speciesId: $speciesId, colorId: $colorId) {
      ...ItemAppearanceForOutfitPreview
    }
  }
}"""
    + FRAGMENT_ITEM_APPEARANCE
    + FRAGMENT_ITEM_PROPERTIES
    + FRAGMENT_PET_APPEARANCE
)

# grab pet appearance by ID
GRAB_PET_APPEARANCE_BY_ID = (
    """
query ($appearanceId: ID!, $size: LayerImageSize!) {
  petAppearanceById(id: $appearanceId) {
    ...PetAppearanceForOutfitPreview
  }    
}
"""
    + FRAGMENT_PET_APPEARANCE
)

# grab pet appearance by ID
GRAB_PET_APPEARANCES_BY_IDS = (
    """
query ($speciesId: ID!, $colorId: ID!, $size: LayerImageSize!) {
  petAppearances(speciesId: $speciesId, colorId: $colorId) {
    ...PetAppearanceForOutfitPreview
  } 
}
"""
    + FRAGMENT_PET_APPEARANCE
)

# grab pet data
PET_ON_NEOPETS = (
    """
query($petName: String!, $size: LayerImageSize!) {
  petOnNeopetsDotCom(petName: $petName) {
    petAppearance {
      ...PetAppearanceForOutfitPreview
    }
    wornItems {
      id
    }
  }
}"""
    + FRAGMENT_PET_APPEARANCE
)

# grab outfit data
OUTFIT = (
    """
query($outfitId: ID!, $size: LayerImageSize!) {
  outfit(id: $outfitId) {
    id
    name
    createdAt
    updatedAt
    creator {
      ...UserProperties
    }
    wornItems {
      ...ItemProperties
    }
    closetedItems {
      ...ItemProperties
    }
    petAppearance {
      ...PetAppearanceForOutfitPreview
    }
  }
}"""
    + FRAGMENT_ITEM_PROPERTIES
    + FRAGMENT_PET_APPEARANCE
    + FRAGMENT_USER_PROPERTIES
)

# grab zones
GRAB_ZONES = """
{
  allZones {
    id
    depth
    label
  }
}"""

# borrowed from DTI, for ensuring a valid pose
CLOSEST_POSES_IN_ORDER = {
    PetPose.HAPPY_MASC: [
        PetPose.HAPPY_MASC,
        PetPose.HAPPY_FEM,
        PetPose.SAD_MASC,
        PetPose.SAD_FEM,
        PetPose.SICK_MASC,
        PetPose.SICK_FEM,
        PetPose.UNCONVERTED,
        PetPose.UNKNOWN,
    ],
    PetPose.HAPPY_FEM: [
        PetPose.HAPPY_FEM,
        PetPose.HAPPY_MASC,
        PetPose.SAD_FEM,
        PetPose.SAD_MASC,
        PetPose.SICK_FEM,
        PetPose.SICK_MASC,
        PetPose.UNCONVERTED,
        PetPose.UNKNOWN,
    ],
    PetPose.SAD_MASC: [
        PetPose.SAD_MASC,
        PetPose.SAD_FEM,
        PetPose.HAPPY_MASC,
        PetPose.HAPPY_FEM,
        PetPose.SICK_MASC,
        PetPose.SICK_FEM,
        PetPose.UNCONVERTED,
        PetPose.UNKNOWN,
    ],
    PetPose.SAD_FEM: [
        PetPose.SAD_FEM,
        PetPose.SAD_MASC,
        PetPose.HAPPY_FEM,
        PetPose.HAPPY_MASC,
        PetPose.SICK_FEM,
        PetPose.SICK_MASC,
        PetPose.UNCONVERTED,
        PetPose.UNKNOWN,
    ],
    PetPose.SICK_MASC: [
        PetPose.SICK_MASC,
        PetPose.SICK_FEM,
        PetPose.SAD_MASC,
        PetPose.SAD_FEM,
        PetPose.HAPPY_MASC,
        PetPose.HAPPY_FEM,
        PetPose.UNCONVERTED,
        PetPose.UNKNOWN,
    ],
    PetPose.SICK_FEM: [
        PetPose.SICK_FEM,
        PetPose.SICK_MASC,
        PetPose.SAD_FEM,
        PetPose.SAD_MASC,
        PetPose.HAPPY_FEM,
        PetPose.HAPPY_MASC,
        PetPose.UNCONVERTED,
        PetPose.UNKNOWN,
    ],
    PetPose.UNCONVERTED: [
        PetPose.UNCONVERTED,
        PetPose.HAPPY_FEM,
        PetPose.HAPPY_MASC,
        PetPose.SAD_FEM,
        PetPose.SAD_MASC,
        PetPose.SICK_FEM,
        PetPose.SICK_MASC,
        PetPose.UNKNOWN,
    ],
    PetPose.UNKNOWN: [
        PetPose.HAPPY_FEM,
        PetPose.HAPPY_MASC,
        PetPose.SAD_FEM,
        PetPose.SAD_MASC,
        PetPose.SICK_FEM,
        PetPose.SICK_MASC,
        PetPose.UNCONVERTED,
        PetPose.UNKNOWN,
    ],
}
