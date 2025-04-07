from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import httpx

from .constants import (
    GRAB_ALL_APPEARANCES_FOR_COLOR,
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
    HTTPException,
    InvalidColorSpeciesPair,
    MissingModelData,
    MissingPetAppearance,
    NeopetNotFound,
    OutfitNotFound,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .enums import LayerImageSize, PetPose
    from .models import Color, Species
    from .types import (
        ID,
        FetchAllAppearancesPayload,
        FetchAssetsPayload,
        FetchedNeopetPayload,
        OutfitPayload,
        PetAppearancePayload,
        ZonePayload,
    )

log: logging.Logger = logging.getLogger(__name__)


class HTTPClient:
    __slots__: tuple[str, ...] = ("_proxy", "_retries")
    API_BASE = "https://impress-2020.openneo.net/api"

    def __init__(
        self,
        *,
        proxy: str | dict[str, str] | None = None,
        retries: int = 3,
    ) -> None:
        self._proxy = proxy
        self._retries = retries

    async def _query(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        **kwargs: dict[str, Any],
    ) -> dict[Any, Any]:
        # for graphql queries
        kwargs["headers"] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
        }

        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient(
            proxy=self._proxy,  # type: ignore
            transport=httpx.AsyncHTTPTransport(retries=self._retries),
        ) as client:
            try:
                response = await client.post(
                    f"{self.API_BASE}/graphql",
                    json=payload,
                    **kwargs,
                )
                return response.json()
            except json.decoder.JSONDecodeError as e:
                raise HTTPException(response, e) from e  # type: ignore
            except httpx.HTTPError as e:
                raise HTTPException(e) from e

    async def _fetch_valid_pet_poses(self) -> bytes:
        return await self._fetch_binary_data(f"{self.API_BASE}/validPetPoses")

    async def _fetch_binary_data(self, url: str) -> bytes:
        async with httpx.AsyncClient(
            proxy=self._proxy,  # type: ignore
            transport=httpx.AsyncHTTPTransport(retries=self._retries),
            limits=httpx.Limits(max_connections=None, max_keepalive_connections=None),
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            return response.read()

    async def fetch_appearance_by_id(
        self,
        *,
        id: int,
        size: LayerImageSize,
    ) -> PetAppearancePayload:
        data = await self._query(
            GRAB_PET_APPEARANCE_BY_ID,
            variables={"appearanceId": str(id), "size": str(size)},
        )

        appearance_data = data["data"]["petAppearanceById"]

        if appearance_data is None:
            raise MissingPetAppearance(f"Pet Appearance ID: {id} not found.")

        return appearance_data

    async def fetch_appearance(
        self,
        *,
        species: Species,
        color: Color,
        pose: PetPose,
        size: LayerImageSize,
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

        appearance = data["data"]["petAppearance"]
        if appearance is None:
            raise MissingPetAppearance(
                f'Pet Appearance <"{species.id}-{color.id}-{pose.name}"> does not exist.',
            )
        return appearance

    async def fetch_appearances(
        self,
        *,
        species: Species,
        color: Color,
        size: LayerImageSize,
    ) -> list[PetAppearancePayload]:
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

    async def fetch_all_zones(self) -> list[ZonePayload]:
        zone_data = await self._query(GRAB_ZONES)
        return zone_data["data"]["allZones"]

    async def fetch_neopet_by_name(
        self,
        name: str,
        size: LayerImageSize,
    ) -> FetchedNeopetPayload:
        data = await self._query(
            query=PET_ON_NEOPETS,
            variables={"petName": name, "size": str(size)},
        )

        # the API responds with an error AND with [data][petOnNeopetsDotCom] being null,
        # so let's just check the latter first
        if "data" not in data:
            # an error we were not prepared for has occurred, let's find it!
            log.critical(f"Unknown pet appearance data returned: {str(data)}")
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data.",
            )

        if errors := data.get("errors"):
            # let's tackle the known errors first...
            # errors are a list of dicts, let's loop for any we know!

            for e in errors:
                if (
                    "This pet's modeling data isn't loaded into our database yet, sorry!"
                    in e["message"]
                ):
                    raise MissingModelData(
                        "This pet's modeling data isn't loaded into DTI yet! Go model it on Classic DTI!",
                    )

            log.critical(f"Unhandled error occurred in data: {str(data)}")
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data.",
            )

        pet_on_neo = data["data"]["petOnNeopetsDotCom"]
        if pet_on_neo is None:
            raise NeopetNotFound("This pet does not seem to exist.")

        return pet_on_neo

    async def fetch_assets_for(
        self,
        *,
        species: Species,
        color: Color,
        pose: PetPose,
        item_ids: Sequence[ID] | None = None,
        item_names: Sequence[str] | None = None,
        size: LayerImageSize | None = None,
    ) -> FetchAssetsPayload:
        # basically the fullest single-purpose dataset we can grab from DTI

        variables: dict[str, Any] = {
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
                f"Somehow, the API returned null for a query. Params: {variables!r}",
            )
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data.",
            )

        if error := data.get("error", None):
            if "it is undefined" in error["message"]:
                raise InvalidColorSpeciesPair(
                    f"According to DTI, the {species} species does not have the color {color}. If it's newly released, it must be modeled first!",
                )

            log.critical(f"Unhandled error occurred in data: {str(data)}")
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data.",
            )

        if "data" not in data:
            # an error we were not prepared for has occurred, let's find it!
            log.critical(f"Unknown pet appearance data returned: {str(data)}")
            raise NeopetNotFound(
                "An error occurred while trying to gather this pet's data.",
            )

        return data["data"]

    async def fetch_appearance_ids(
        self,
        *,
        species: Species,
        color: Color,
    ) -> list[int]:
        data = await self._query(
            GRAB_PET_APPEARANCE_IDS,
            variables={"speciesId": species.id, "colorId": color.id},
        )

        return [int(appearance["id"]) for appearance in data["data"]["petAppearances"]]

    async def fetch_all_appearances_for_color(
        self,
        color: Color,
        /,
        item_ids: list[int],
        size: LayerImageSize,
    ) -> FetchAllAppearancesPayload:
        data = await self._query(
            GRAB_ALL_APPEARANCES_FOR_COLOR,
            variables={
                "itemIds": item_ids,
                "preferredColorId": color.id,
                "size": str(size),
            },
        )

        return data["data"]
