import asyncio

from dti import Client
from dti.errors import NeopetNotFound


async def main():
    dti_client = Client()

    try:
        pet = await dti_client.get_neopet_by_name("diceroll123456789")

        with open("./pet.png", "wb") as fp:
            await pet.render(fp)
    except NeopetNotFound as e:
        # raised if the pet by that name does not exist
        print(e)


asyncio.run(main())
