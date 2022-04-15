from dti import Client


def test_state_data_existing(client: Client):
    assert client._state._valid_pairs.full_data != b""


def test_state_data(client: Client):
    # the code does this already but let's have a test anyways
    field = client._state._valid_pairs
    assert field.species_count * field.color_count == len(field.data)
