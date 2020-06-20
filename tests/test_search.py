import pytest

from dti import Client
from tests import TEST_ITEM, TEST_PET


@pytest.mark.asyncio
async def test_query_search() -> None:
    client = Client()
    found = False

    async for item in client.search(query=TEST_ITEM.name):
        if item.name == TEST_ITEM.name and item.id == TEST_ITEM.id:
            found = True

    assert found


@pytest.mark.asyncio
async def test_item_id_search() -> None:
    client = Client()
    found = False

    async for item in client.search(item_ids=[TEST_ITEM.id]):
        if item.name == TEST_ITEM.name and item.id == TEST_ITEM.id:
            found = True

    assert found


@pytest.mark.asyncio
async def test_wearable_search() -> None:
    client = Client()
    found = False

    async for item in client.search(
        query=TEST_ITEM.name, species_id=TEST_PET.species, color_id=TEST_PET.color
    ):
        if item.name == TEST_ITEM.name and item.id == TEST_ITEM.id:
            found = True

    assert found


@pytest.mark.asyncio
async def test_flat_search() -> None:
    client = Client()
    query = "pile of dung"  # currently, there are 2 search results for this
    expected = 2  # so we'll also use this as a limit, just in case

    items = await client.search(query=query).flatten()

    assert len(items) >= expected
