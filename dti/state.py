import asyncio
import contextlib
import time
from typing import Optional, Union, TYPE_CHECKING

from .constants import ALL_SPECIES_AND_COLORS
from .enums import PetPose
from .errors import InvalidPairBytes
from .http import HTTPClient

if TYPE_CHECKING:
    from . import Color, Species


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


class BitField(int):
    """Represents the bit field of a color+species combo. This number holds the data of whether
    or not the associated color+species has specific :class:`PetPose`s. The poses each have a
    power-of-two value, which are bitwise OR'd together to make this object's value.
    """

    __slots__ = ()

    def check(self, pose: Union[PetPose, int]) -> bool:
        """:class:`bool`: Returns whether or not this bit field contains the supplied pose."""
        return (self & pose) == pose

    @property
    def happy_masc(self) -> bool:
        """:class:`bool`: Returns whether or not this bit field contains the HAPPY_MASC pose."""
        return (self & 1) == 1

    @property
    def sad_masc(self) -> bool:
        """:class:`bool`: Returns whether or not this bit field contains the SAD_MASC pose."""
        return (self & 2) == 2

    @property
    def sick_masc(self) -> bool:
        """:class:`bool`: Returns whether or not this bit field contains the SICK_MASC pose."""
        return (self & 4) == 4

    @property
    def happy_fem(self) -> bool:
        """:class:`bool`: Returns whether or not this bit field contains the HAPPY_FEM pose."""
        return (self & 8) == 8

    @property
    def sad_fem(self) -> bool:
        """:class:`bool`: Returns whether or not this bit field contains the SAD_FEM pose."""
        return (self & 16) == 16

    @property
    def sick_fem(self) -> bool:
        """:class:`bool`: Returns whether or not this bit field contains the SICK_FEM pose."""
        return (self & 32) == 32

    @property
    def unconverted(self) -> bool:
        """:class:`bool`: Returns whether or not this bit field contains the UNCONVERTED pose."""
        return (self & 64) == 64

    @property
    def unknown(self) -> bool:
        """:class:`bool`: Returns whether or not this bit field contains the UNKNOWN pose."""
        return (self & 128) == 128


class ValidField:
    __slots__ = ("species_count", "color_count", "_data")

    def __init__(self, data: Optional[bytes] = None):
        if data is None:
            self.species_count = 0
            self.color_count = 0
            return
        # the first byte is the amount of species
        # the second byte is the amount of colors
        # this pops them off the data table so we can cleanly search later :)
        self.species_count, self.color_count, *self._data = data

        # this next if statement makes sure the above data is correct
        if self.species_count * self.color_count != len(self._data):
            raise InvalidPairBytes("Invalid Pet-Pose bit table")

    def _get_bit(self, species_id: int, color_id: int) -> BitField:
        species_id -= 1
        color_id -= 1
        return BitField(self._data[species_id * self.color_count + color_id])

    def _check(
        self,
        *,
        species_id: int,
        color_id: int,
        pose: Optional[PetPose] = None,
    ) -> bool:
        bit = self._get_bit(species_id, color_id)

        if pose is None:
            return bit > 0

        return bit.check(pose)


class State:
    __slots__ = (
        "_http",
        "_lock",
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
        self._last_update = 0.0

        # 1h by default, 10s minimum to be kind to the API
        cache_timeout = cache_timeout or 3600
        cache_timeout = max(cache_timeout, 10)
        self._cache_timeout = cache_timeout

        # _valid_pairs is (going to be) a bit array field of sorts.
        self._valid_pairs = ValidField()

        # this lock is so only one thing accesses the state at a time between checking if updates are needed + updating
        self._lock = asyncio.Lock()

        # this lock is so updating only happens once at a time, since it can be manually called
        self._update_lock = asyncio.Lock()

        self._http = HTTPClient()

    async def _fetch_species_and_color(self):
        data = await self._http._query(query=ALL_SPECIES_AND_COLORS)
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
        await self._update()
        async with self._lock:
            return self._species[species]

    async def _get_color(self, color: Union[int, str]) -> Optional["Color"]:
        await self._update()
        async with self._lock:
            return self._colors[color]

    async def _get_bit(self, *, species_id: int, color_id: int) -> BitField:
        await self._update()
        async with self._lock:
            return self._valid_pairs._get_bit(species_id=species_id, color_id=color_id)

    async def _check(
        self, *, species_id: int, color_id: int, pose: Optional[PetPose] = None
    ) -> bool:
        await self._update()
        async with self._lock:
            return self._valid_pairs._check(
                species_id=species_id, color_id=color_id, pose=pose
            )

    async def _update(self, force: Optional[bool] = False):
        async with self._update_lock:
            # forces cache, if outdated
            if force is False and not self.is_outdated:
                return self

            self._valid_pairs = ValidField()
            self._cached = False
            self._colors.clear()
            self._species.clear()

            self._valid_pairs = ValidField(await self._http._fetch_valid_pet_poses())
            await self._fetch_species_and_color()

            self._cached = True
            self._last_update = time.monotonic()
            return self
