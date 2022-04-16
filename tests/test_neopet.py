from typing import Any, Dict

import pytest
from dti.client import Client
from dti.enums import LayerImageSize
from dti.models import Item, Neopet, PetAppearance


async def _neopet_from_data(client: Client, data: Dict[str, Any]):
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


@pytest.mark.asyncio
async def test_neopet(client: Client, assets_data: Dict[str, Any]):
    neopet = await _neopet_from_data(client, assets_data)
    # successfully building a Neopet object is the test
    assert neopet.species.name == "Krawk"


@pytest.mark.asyncio
async def test_neopet_render_layers(client: Client, assets_data: Dict[str, Any]):
    neopet = await _neopet_from_data(client, assets_data)
    layers = neopet.appearance._render_layers(neopet.items)
    assert len(layers) == 12


@pytest.mark.asyncio
async def test_neopet_render_layers_unwearable(
    client: Client, assets_data_unwearable: Dict[str, Any]
):
    # this is a Baby Pteri wearing Kiss of Hearts + Baby Zomutt Contacts
    # the items should be filtered off, as they can't actually be worn by this pet,
    # leaving just the pet layer
    neopet = await _neopet_from_data(client, assets_data_unwearable)
    layers = neopet.appearance._render_layers(neopet.items)
    assert len(layers) == 1
