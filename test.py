import asyncio

import dti


async def main():
    dti_client = dti.Client()

    pet = await dti_client.search(query="Shining hall of mirrors background")

    # try:
    #     pet = await dti_client.get_neopet_by_name("arosy")
    #
    #     with open("./pet.png", "wb") as fp:
    #         await pet.render(fp)
    # except dti.NeopetNotFound as e:
    #     # raised if the pet by that name does not exist
    #     print(e)

    # color = await dti_client.get_color("Blueberry")
    # print(await color.missing_species())

    # for color in await dti_client.all_colors():
    #     if len(await color.species()) <= 2:
    #         print(color.id, color.name)

    # try:
    #     species = await dti_client.get_species("Moehog")
    #     color = await dti_client.get_color("Blue")
    #     pet = await dti_client.get_neopet(
    #         color=color,
    #         species=species,
    #         pose=dti.PetPose.HAPPY_MASC,
    #         item_ids=[81062, 74551],
    #     )
    #
    #     # for item in pet.items:
    #     #     print(item)
    #     #     for layer in item.appearance.restricted_zones:
    #     #         print("restricts", layer)
    #     #     for layer in item.appearance.layers:
    #     #         print("occupies", layer.zone)
    #     #     print("-" * 20)
    #
    #     with open("./pet.png", "wb") as fp:
    #         await pet.render(fp)
    # except dti.NeopetNotFound as e:
    #     # raised if the pet by that name does not exist
    #     print(e)


asyncio.run(main())
