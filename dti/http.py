from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Union

import httpx

from .constants import (
    GRAB_PET_APPEARANCE_BY_ID,
    GRAB_PET_APPEARANCE_BY_SPECIES_COLOR_POSE,
    GRAB_PET_APPEARANCE_IDS,
    GRAB_PET_APPEARANCE_WITH_ITEMS_BY_IDS,
    GRAB_PET_APPEARANCE_WITH_ITEMS_BY_NAMES,
    GRAB_PET_APPEARANCES_BY_IDS,
    GRAB_ZONES,
    OUTFIT,
    PET_ON_NEOPETS,
)
from .errors import (
    InvalidColorSpeciesPair,
    MissingPetAppearance,
    NeopetNotFound,
    OutfitNotFound,
)

if TYPE_CHECKING:
    from .enums import LayerImageSize, PetPose
    from .models import Color, Species
    from .types import (
        FetchAssetsPayload,
        FetchedNeopetPayload,
        OutfitPayload,
        PetAppearancePayload,
        ZonePayload,
    )

log = logging.getLogger(__name__)


class HTTPClient:
    __slots__ = ("_proxy",)
    API_BASE = "https://impress-2020.openneo.net/api"

    def __init__(self, *, proxy: Optional[str] = None):
        self._proxy = proxy

    async def _query(self, query, variables=None, **kwargs) -> Dict:
        # for graphql queries
        kwargs["headers"] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient(
            proxies=self._proxy, transport=httpx.AsyncHTTPTransport(retries=3)
        ) as client:
            response = await client.post(
                f"{self.API_BASE}/graphql", json=payload, **kwargs
            )
            return response.json()

    async def _fetch_valid_pet_poses(self) -> bytes:
        return await self._fetch_binary_data(self.API_BASE + "/validPetPoses")

    async def _fetch_binary_data(self, url: str) -> bytes:
        async with httpx.AsyncClient(
            proxies=self._proxy, transport=httpx.AsyncHTTPTransport(retries=3)
        ) as client:
            response = await client.get(url)
            return response.read()

    async def fetch_appearance_by_id(
        self, *, id: int, size: LayerImageSize
    ) -> PetAppearancePayload:
        data = await self._query(
            GRAB_PET_APPEARANCE_BY_ID, variables={"appearanceId": id, "size": str(size)}
        )

        appearance_data = data["data"]["petAppearanceById"]

        if appearance_data is None:
            raise MissingPetAppearance(f"Pet Appearance ID: {id} not found.")

        return appearance_data

    async def fetch_appearance(
        self, *, species: Species, color: Color, pose: PetPose, size: LayerImageSize
    ) -> PetAppearancePayload:
        data = await self._query(
            GRAB_PET_APPEARANCE_BY_SPECIES_COLOR_POSE,
            variables={
                "speciesId": species.id,
                "colorId": color.id,
                "size": str(size),
                "pose": str(pose),
            },
        )

        return data["data"]["petAppearance"]

    async def fetch_appearances(
        self, *, species: Species, color: Color, size: LayerImageSize
    ) -> List[PetAppearancePayload]:
        data = await self._query(
            GRAB_PET_APPEARANCES_BY_IDS,
            variables={"speciesId": species.id, "colorId": color.id, "size": str(size)},
        )

        return data["data"]["petAppearances"]

    async def fetch_outfit(self, *, id: int, size: LayerImageSize) -> OutfitPayload:
        data = await self._query(OUTFIT, variables={"outfitId": id, "size": str(size)})

        outfit_data = data["data"]["outfit"]

        if outfit_data is None:
            raise OutfitNotFound(f"Outfit (ID: {id}) not found.")

        return outfit_data

    async def fetch_all_zones(self) -> List[ZonePayload]:
        zone_data = await self._query(GRAB_ZONES)
        return zone_data["data"]["allZones"]

    async def fetch_neopet_by_name(
        self, name: str, size: LayerImageSize
    ) -> FetchedNeopetPayload:
        data = await self._query(
            query=PET_ON_NEOPETS,
            variables={"petName": name, "size": str(size)},
        )

        # the API responds with an error AND with [data][petOnNeopetsDotCom] being null,
        # so let's just check the latter first
        if "data" not in data:
            # an error we were not prepared for has occurred, let's find it!
            log.critical("Unknown pet appearance data returned: " + str(data))
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data."
            )

        pet_on_neo = data["data"]["petOnNeopetsDotCom"]
        if pet_on_neo is None:
            raise NeopetNotFound("This pet does not seem to exist.")

        error = data.get("errors")
        if error:
            log.critical("Unhandled error occurred in data: " + str(data))
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data."
            )

        return pet_on_neo

    async def fetch_assets_for(
        self,
        *,
        species: Species,
        color: Color,
        pose: PetPose,
        item_ids: Optional[Sequence[Union[str, int]]] = None,
        item_names: Optional[Sequence[str]] = None,
        size: Optional[LayerImageSize] = None,
    ) -> FetchAssetsPayload:
        # basically the fullest single-purpose dataset we can grab from DTI

        variables = {
            "speciesId": species.id,
            "colorId": color.id,
            "size": str(size),
            "pose": str(pose),
        }

        if item_names:
            variables["names"] = item_names or []
            query = GRAB_PET_APPEARANCE_WITH_ITEMS_BY_NAMES
        else:
            variables["allItemIds"] = item_ids or []
            query = GRAB_PET_APPEARANCE_WITH_ITEMS_BY_IDS

        data = await self._query(query=query, variables=variables)

        if data is None:
            # an error we were not prepared for has occurred, let's find it!
            log.critical(
                f"Somehow, the API returned null for a query. Params: {variables!r}"
            )
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data."
            )

        error = data.get("error", None)
        if error:
            if "it is undefined" in error["message"]:
                raise InvalidColorSpeciesPair(
                    f"According to DTI, the {species} species does not have the color {color}. If it's newly released, it must be modeled first!"
                )

            log.critical("Unhandled error occurred in data: " + str(data))
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data."
            )

        if "data" not in data:
            # an error we were not prepared for has occurred, let's find it!
            log.critical("Unknown pet appearance data returned: " + str(data))
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data."
            )

        return data["data"]

    async def fetch_appearance_ids(
        self, *, species: Species, color: Color
    ) -> List[int]:
        data = await self._query(
            GRAB_PET_APPEARANCE_IDS,
            variables=dict(speciesId=species.id, colorId=color.id),
        )

        return [int(appearance["id"]) for appearance in data["data"]["petAppearances"]]
