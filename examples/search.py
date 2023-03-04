import asyncio

from dti import Client


async def main() -> None:
    dti_client = Client()
    async for item in dti_client.search(item_ids=[81162]):
        print(item)


asyncio.run(main())
