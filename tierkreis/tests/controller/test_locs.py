import pytest

from tierkreis.controller.data.location import Loc

node_location_1 = Loc()
node_location_1 = node_location_1.N(0)
node_location_1 = node_location_1.L(0)
node_location_1 = node_location_1.N(3)
node_location_1 = node_location_1.L(2)
node_location_1 = node_location_1.N(0)
node_location_1 = node_location_1.M("map_port")
node_location_1 = node_location_1.N(0)


node_location_2 = Loc()
node_location_2 = node_location_2.N(0)
node_location_2 = node_location_2.L(0)
node_location_2 = node_location_2.N(3)
node_location_2 = node_location_2.N(8)
node_location_2 = node_location_2.N(0)

node_location_3 = Loc()
node_location_3 = node_location_3.N(0)

node_location_4 = Loc()


@pytest.mark.parametrize(
    ["node_location", "loc_str"],
    [
        (node_location_1, "-.N0.L0.N3.L2.N0.Mmap_port.N0"),
        (node_location_2, "-.N0.L0.N3.N8.N0"),
        (node_location_3, "-.N0"),
        (node_location_4, "-"),
    ],
)
def test_to_from_str(node_location: Loc, loc_str: str):
    node_location_str = str(node_location)
    assert node_location_str == loc_str

    new_loc = Loc(node_location_str)
    assert new_loc == node_location
