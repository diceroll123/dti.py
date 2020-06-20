import pytest

from dti import Client
from tests import TEST_ITEM, TEST_PET


@pytest.mark.asyncio
async def test_statefulness() -> None:
    client = Client()
    found = False

    async for item in client.search(query=TEST_ITEM.name):
        if item.name == TEST_ITEM.name and item.id == TEST_ITEM.id:
            found = True

    pet = await client.get_neopet(color=TEST_PET.color, species=TEST_PET.species)

    assert found and pet
