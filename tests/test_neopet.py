from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from dti.enums import LayerImageSize
from dti.models import Item, Neopet, PetAppearance

if TYPE_CHECKING:
    from dti.client import Client


async def _neopet_from_data(client: Client, data: dict[str, Any]) -> Neopet:
    state = client._state
    size = LayerImageSize.SIZE_600

    items = [
        Item(data=item, state=state)
        for item in data["data"]["items"]
        if item is not None
    ]

    appearance = PetAppearance(
        data=data["data"]["petAppearance"],
        size=size,
        state=state,
    )

    species = appearance.species
    color = appearance.color
    pose = appearance.pose

    bit = await state._get_bit(species_id=species.id, color_id=color.id)

    return Neopet(
        species=species,
        color=color,
        pose=pose,
        valid_poses=bit,
        items=items,
        appearance=appearance,
        name="",
        size=size,
        state=state,
    )


@pytest.mark.asyncio()
async def test_neopet(client: Client, assets_data: dict[str, Any]) -> None:
    neopet = await _neopet_from_data(client, assets_data)
    # successfully building a Neopet object is the test
    assert neopet.species.name == "Krawk"


@pytest.mark.asyncio()
async def test_neopet_render_layers(
    client: Client,
    assets_data: dict[str, Any],
) -> None:
    neopet = await _neopet_from_data(client, assets_data)
    layers = neopet.appearance._render_layers(neopet.items)
    assert len(layers) == 12


@pytest.mark.asyncio()
async def test_neopet_render_layers_unwearable(
    client: Client,
    assets_data_unwearable: dict[str, Any],
) -> None:
    # this is a Baby Pteri wearing Kiss of Hearts + Baby Zomutt Contacts
    # the items should be filtered off, as they can't actually be worn by this pet,
    # leaving just the pet layer
    neopet = await _neopet_from_data(client, assets_data_unwearable)
    layers = neopet.appearance._render_layers(neopet.items)
    assert len(layers) == 1


@pytest.mark.asyncio()
async def test_neopet_render_layers_covers_biology(
    client: Client,
    assets_data_covers_biology: dict[str, Any],
) -> None:
    # this is a Blue Bruce wearing Bruce Brucey B Glasses, Bruce Brucey B Mouth, Bruce Brucey B Necklace, Bruce Brucey B Shirt
    # the mouth covers the actual Bruce mouth
    neopet = await _neopet_from_data(client, assets_data_covers_biology)
    layers = neopet.appearance._render_layers(neopet.items)

    # Without the mouth being overriden, there would be 8 layers.
    assert len(layers) == 7
