from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from dti import Client
from dti.models import Color, Species
from dti.state import ValidField, _NameDict

dti_c = Client()

tests = Path("./tests")
payloads = tests / "payloads"

# inject our test binary
dti_c._state._valid_pairs = ValidField((tests / "test_pet_data.bin").read_bytes())

# set the last update time to now
dti_c._state._cached = True
dti_c._state._last_update = time.monotonic()

# inject species and colors
# data from State._fetch_species_and_color
data = json.loads((payloads / "state__fetch_species_and_color.json").read_text())
dti_c._state._colors = _NameDict(
    {c["id"]: Color(data=c, state=dti_c._state) for c in data["data"]["allColors"]},
)
dti_c._state._species = _NameDict(
    {s["id"]: Species(data=s, state=dti_c._state) for s in data["data"]["allSpecies"]},
)


@pytest.fixture()
def client() -> Client:
    return dti_c


@pytest.fixture()
def zone_data() -> dict[str, Any]:
    # zone payload from Client.fetch_all_zones()
    return json.loads((payloads / "client_fetch_all_zones.json").read_text())


@pytest.fixture()
def outfit_data() -> dict[str, Any]:
    # outfit payload from Client.fetch_outfit()
    return json.loads((payloads / "client_fetch_outfit.json").read_text())


@pytest.fixture()
def assets_data() -> dict[str, Any]:
    # petAppearance payload from Neopet._fetch_assets_for()
    return json.loads((payloads / "neopet__fetch_assets_for.json").read_text())


@pytest.fixture()
def assets_data_unwearable() -> dict[str, Any]:
    # petAppearance payload from Neopet._fetch_assets_for()
    return json.loads(
        (payloads / "neopet__fetch_assets_for__unwearable.json").read_text(),
    )


@pytest.fixture()
def assets_data_covers_biology() -> dict[str, Any]:
    # petAppearance payload from Neopet._fetch_assets_for()
    return json.loads(
        (payloads / "neopet__fetch_assets_for__covers_biology.json").read_text(),
    )
