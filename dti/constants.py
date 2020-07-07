# fragments
from .enums import PetPose

FRAGMENT_PET_APPEARANCE = """
fragment PetAppearanceForOutfitPreview on PetAppearance {
  id
  pose
  color {
    id
    name
  }
  species {
    id
    name
  }
  bodyId
  petStateId
  layers {
    imageUrl(size: $size)
    zone {
      id
      depth
      label
    }
  }
}"""


FRAGMENT_ITEM_APPEARANCE = """
fragment ItemAppearanceForOutfitPreview on ItemAppearance {
  restrictedZones {
    id
    depth
    label
  }
  layers {
    imageUrl(size: $size)
    zone {
      id
      depth
      label
    }
  }
}"""

FRAGMENT_ITEM_SEARCH_RESULT = """
fragment ItemResult on ItemSearchResult {
  items {
    id
    name
    description
    thumbnailUrl
    rarityIndex
    isNc
    appearanceOn(speciesId: $speciesId, colorId: $colorId) {
      ...ItemAppearanceForOutfitPreview
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
SEARCH_ITEM_IDS = """
query($itemIds: [ID!]!) {
  items(ids: $itemIds) {
    id
    name
    description
    thumbnailUrl
    rarityIndex
    isNc
  }
}"""

SEARCH_TO_FIT = (
    """
query($query: String!, $speciesId: ID!, $colorId: ID!, $offset: Int, $limit: Int, $size: LayerImageSize!) {
  itemSearchToFit(query: $query, speciesId: $speciesId, colorId: $colorId, offset: $offset, limit: $limit) {
    ...ItemResult
  }
}"""
    + FRAGMENT_ITEM_APPEARANCE
    + FRAGMENT_ITEM_SEARCH_RESULT
)

SEARCH_QUERY = """
query($query: String!) {
  itemSearch(query: $query) {
    items {
      id
      name
      description
      thumbnailUrl
      rarityIndex
      isNc
    }
  }
}"""

# grab pet appearances
GRAB_PET_APPEARANCES = (
    """
query ($allItemIds: [ID!]!, $speciesId: ID!, $colorId: ID!, $size: LayerImageSize!) {
  petAppearances(speciesId: $speciesId, colorId: $colorId) {
    ...PetAppearanceForOutfitPreview
  }
  items(ids: $allItemIds) {
    id
    name
    description
    thumbnailUrl
    rarityIndex
    isNc
    appearanceOn(speciesId: $speciesId, colorId: $colorId) {
      ...ItemAppearanceForOutfitPreview
    }
  }
}"""
    + FRAGMENT_PET_APPEARANCE
    + FRAGMENT_ITEM_APPEARANCE
)

# grab pet data
PET_ON_NEOPETS = """
query($petName: String!) {
  petOnNeopetsDotCom(petName: $petName) {
    pose
    species {
      id
    }
    color {
      id
    }
    items {
      id
    }
  }
}"""

# grab outfit data
OUTFIT = """
query($outfitId: ID!, $size: LayerImageSize!) {
  outfit(id: $outfitId) {
    id
    name
    wornItems {
      id
      name
      description
      thumbnailUrl
      rarityIndex
      isNc
    }
    closetedItems {
      id
      name
      description
      thumbnailUrl
      rarityIndex
      isNc
    }
    petAppearance {
      id
      pose
      bodyId
      petStateId
      color {
        id
        name
      }
      species {
        id
        name
      }
      layers {
        imageUrl(size: $size)
        zone {
          id
          depth
          label
        }
      }
    }
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
