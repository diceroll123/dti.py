from typing import Any, Dict

from dti.models import Zone


def test_zones(zone_data: Dict[str, Any]) -> None:
    zones = [Zone(data=d) for d in zone_data["data"]["allZones"]]

    # shouldn't ever change
    test_zone = Zone(data={"id": "1", "depth": 1, "label": "Music"})

    assert zones[0] == test_zone
