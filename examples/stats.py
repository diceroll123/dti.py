import asyncio

from dti import Client


async def main() -> None:
    dti_client = Client()
    sorted_species = sorted(await dti_client.all_species(), key=lambda s: s.name)
    for species in sorted_species:
        print(
            f"{species.name} can have this many colors: {len(await species.colors())}",
        )


asyncio.run(main())
