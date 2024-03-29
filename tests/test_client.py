from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import pytest

from dti.enums import PetPose
from dti.errors import InvalidColor, InvalidSpecies
from dti.models import Color, Species

if TYPE_CHECKING:
    from dti import Client


class Combo(NamedTuple):
    species: str
    color: str
    pose: PetPose | None = None


# exists as a valid color + species + pose
VALID = Combo(species="Grundo", color="Mallow", pose=PetPose.UNCONVERTED)

# invalid color + species pair
INVALID = Combo(species="Aisha", color="Coconut", pose=PetPose.UNCONVERTED)

NONEXISTANT = "a4c0d35c95a63a805915367dcfe6b751"  # nonexistant string to look up as a species/color


@pytest.mark.asyncio()
async def test_get_species(client: Client) -> None:
    assert isinstance(await client.get_species(VALID.species), Species)


@pytest.mark.asyncio()
async def test_get_species_nonexistant(client: Client) -> None:
    with pytest.raises(InvalidSpecies):
        assert await client.get_species(NONEXISTANT)


@pytest.mark.asyncio()
async def test_get_color(client: Client) -> None:
    assert isinstance(await client.get_color(VALID.color), Color)


@pytest.mark.asyncio()
async def test_get_color_nonexistant(client: Client) -> None:
    with pytest.raises(InvalidColor):
        assert await client.get_color(NONEXISTANT)


@pytest.mark.asyncio()
async def test_get_all_species(client: Client) -> None:
    assert len(await client.all_species()) > 0


@pytest.mark.asyncio()
async def test_get_all_colors(client: Client) -> None:
    assert len(await client.all_colors()) > 0


@pytest.mark.asyncio()
async def test_get_bit(client: Client) -> None:
    assert await client.get_bit(species=VALID.species, color=VALID.color) > 0


@pytest.mark.asyncio()
async def test_get_bit_invalid(client: Client) -> None:
    # invalid as in the species + color exist, but not as a color for the species.
    # I'm 99.999% sure this combination won't happen, but if it does some day we'll change the test
    assert await client.get_bit(species=INVALID.species, color=INVALID.color) == 0


@pytest.mark.asyncio()
async def test_get_bit_nonexistant_species(client: Client) -> None:
    with pytest.raises(InvalidSpecies):
        assert await client.get_bit(species=NONEXISTANT, color=VALID.color)


@pytest.mark.asyncio()
async def test_get_bit_nonexistant_color(client: Client) -> None:
    with pytest.raises(InvalidColor):
        assert await client.get_bit(species=VALID.species, color=NONEXISTANT)


@pytest.mark.asyncio()
async def test_check(client: Client) -> None:
    assert await client.check(species=VALID.species, color=VALID.color)


@pytest.mark.asyncio()
async def test_check_with_pose(client: Client) -> None:
    assert await client.check(species=VALID.species, color=VALID.color, pose=VALID.pose)


@pytest.mark.asyncio()
async def test_check_invalid(client: Client) -> None:
    assert await client.check(species=INVALID.species, color=INVALID.color) is False
