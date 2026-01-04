from __future__ import annotations

from dti.enums import PetPose
from dti.utils import outfit_image_url


def test_outfit_image_url() -> None:
    url = outfit_image_url(
        species=1,
        color=8,
        pose=PetPose.HAPPY_FEM,
        style=90030,
        item_ids=[74967, 37002, 71526],
    )
    assert (
        url == "https://impress.openneo.net/outfits/new.png?"
        "species=1&color=8&pose=HAPPY_FEM&style=90030&"
        "objects%5B%5D=74967&objects%5B%5D=37002&objects%5B%5D=71526"
    )
