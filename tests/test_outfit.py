from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, Dict

from dti.enums import LayerImageSize
from dti.models import Outfit

if TYPE_CHECKING:
    from dti.client import Client


def test_outfit(client: Client, outfit_data: Dict[str, Any]) -> None:
    # If this breaks, we're probably just missing some new required attribute somewhere
    # We also let this take care of the following models instance tests:
    # dti.Item
    # dti.User
    # dti.PetAppearance

    outfit = Outfit(
        state=client._state,
        size=LayerImageSize.SIZE_600,
        data=outfit_data["data"]["outfit"],
    )
    assert outfit.id == 902792
    assert outfit.name == "Alex (Clockwork Orange)"
    assert outfit.creator and outfit.creator.username == "diceroll123"
    assert outfit.created_at == datetime.datetime(
        2015, 5, 6, 2, 37, 32, tzinfo=datetime.timezone.utc
    )
