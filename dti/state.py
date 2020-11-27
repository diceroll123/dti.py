import asyncio
import contextlib
import time
from typing import Optional, Union

from .constants import ALL_SPECIES_AND_COLORS
from .enums import PetPose
from .errors import InvalidPairBytes
from .http import HTTPClient


class _NameDict(dict):
    # this is only to be used by DTIState
    # for the sole purpose of easily searching colors/species by name
    # that said, we're throwing away any error prevention outside of these rules
    def __getitem__(self, key):
        key = str(key)
        # will never raise a KeyError, but will return None instead
        with contextlib.suppress(KeyError):
            # this is the normal __getitem__ behavior
            return dict.__getitem__(self, key)

        # look for names now
        # lowercase to make it less annoying to search
        key = key.lower()
        for v in self.values():
            if key == v.name.lower():
                return v
        return None


class ValidField:
    __slots__ = ("species_count", "color_count", "_data")

    def __init__(self, data: bytes):
        # the first byte is the amount of species
        # the second byte is the amount of colors
        # this pops them off the data table so we can cleanly search later :)
        self.species_count, self.color_count, *self._data = data

        # this next if statement makes sure the above data is correct
        if self.species_count * self.color_count != len(self._data):
            raise InvalidPairBytes("Invalid Pet-Pose bit table")

    def _get_bit(self, species_id: int, color_id: int) -> int:
        species_id -= 1
        color_id -= 1
        return self._data[species_id * self.color_count + color_id]

    def check(
        self, *, species_id: int, color_id: int, pose: Optional[PetPose] = None,
    ) -> bool:
        bit = self._get_bit(species_id, color_id)

        if pose is None:
            return bit > 0

        find = int(pose)
        return (bit & find) == find


class State:
    __slots__ = (
        "http",
        "lock",
        "_update_lock",
        "_valid_pairs",
        "_colors",
        "_species",
        "_cached",
        "_last_update",
        "_cache_timeout",
    )

    def __init__(self, cache_timeout: Optional[int] = None):
        # colors and species below are accessed by the string version of their ID AND/OR lower-cased names
        # alternatively you can list them out by doing self._colors.values()
        self._colors = _NameDict()
        self._species = _NameDict()
        self._cached = False
        self._last_update = None

        # 1h by default, 10s minimum to be kind to the API
        cache_timeout = cache_timeout or 3600
        if cache_timeout < 10:
            cache_timeout = 10
        self._cache_timeout = cache_timeout

        # _valid_pairs is (going to be) a bit array field of sorts.
        self._valid_pairs = None

        # this lock is so only one thing accesses the state at a time between checking if updates are needed + updating
        self.lock = asyncio.Lock()

        # this lock is so updating only happens once at a time, since it can be manually called
        self._update_lock = asyncio.Lock()

        self.http = HTTPClient()

    async def _grab_species_and_color(self):
        data = await self.http.query(query=ALL_SPECIES_AND_COLORS)
        data = data["data"]
        from .models import Color, Species

        # colors
        self._colors = _NameDict(
            {color["id"]: Color(data=color, state=self) for color in data["allColors"]}
        )

        # species
        self._species = _NameDict(
            {
                species["id"]: Species(data=species, state=self)
                for species in data["allSpecies"]
            }
        )

    @property
    def is_cached(self) -> bool:
        return self._cached

    @property
    def last_update(self) -> float:
        return self._last_update

    @property
    def is_outdated(self) -> bool:
        if self._last_update is None or self._cached is False:
            return True
        return self._last_update < time.monotonic() - self._cache_timeout

    async def _get_species(self, species: Union[int, str]) -> Optional["Species"]:
        await self.update()
        async with self.lock:
            return self._species[species]

    async def _get_color(self, color: Union[int, str]) -> Optional["Color"]:
        await self.update()
        async with self.lock:
            return self._colors[color]

    async def _get_bit(self, *, species_id: int, color_id: int) -> int:
        await self.update()
        async with self.lock:
            return self._valid_pairs._get_bit(species_id=species_id, color_id=color_id)

    async def _check(
        self, *, species_id: int, color_id: int, pose: Optional[PetPose] = None
    ) -> bool:
        await self.update()
        async with self.lock:
            return self._valid_pairs.check(
                species_id=species_id, color_id=color_id, pose=pose
            )

    async def update(self, force: Optional[bool] = False):
        async with self._update_lock:
            # forces cache, if outdated
            if force is False:
                if not self.is_outdated:
                    return self

            self._valid_pairs = None
            self._cached = False
            self._colors.clear()
            self._species.clear()

            self._valid_pairs = ValidField(await self.http.get_valid_pet_poses())
            await self._grab_species_and_color()

            self._cached = True
            self._last_update = time.monotonic()
            return self
