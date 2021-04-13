import pytest

from dti import Client, InvalidColorSpeciesPair, NeopetNotFound


@pytest.mark.asyncio
async def test_uncached_call() -> None:
    client = Client()

    cacheless_before = client._state.is_cached is False
    await client.get_species("Red")
    assert cacheless_before and client._state.is_cached


@pytest.mark.asyncio
async def test_impossible_pet() -> None:
    client = Client()
    with pytest.raises(InvalidColorSpeciesPair):
        await client.fetch_neopet(color="Apple", species="Aisha")


@pytest.mark.asyncio
async def test_impossible_pet_name() -> None:
    client = Client()
    with pytest.raises(NeopetNotFound):
        await client.fetch_neopet_by_name("thyassa_thyassa_thyassa")  # too long!
