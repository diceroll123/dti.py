from collections import namedtuple

TestPet = namedtuple("TestPet", "color species")
TestItem = namedtuple("TestItem", "id name")

TEST_PET = TestPet(color=61, species=2)  # Red Aisha
TEST_ITEM = TestItem(id=47710, name="Molten Pile of Dung")  # wearable by any pet
