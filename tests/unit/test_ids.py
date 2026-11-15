from spaceapp.platform.ids import DEFAULT_HABITAT_CODE, habitat_id, sensor_id, stable_uuid, zone_id


def test_the_same_names_always_give_the_same_uuid():
    assert stable_uuid("zone", "ship", "lab") == stable_uuid("zone", "ship", "lab")


def test_different_zones_and_habitats_never_collide():
    codes = ["eng", "eclss", "lab", "med", "bridge", "air", "store", "gym", "galley", "crew"]
    ids = {zone_id(DEFAULT_HABITAT_CODE, c) for c in codes}
    assert len(ids) == 10
    assert zone_id("ship-a", "lab") != zone_id("ship-b", "lab")
    assert habitat_id() != zone_id(DEFAULT_HABITAT_CODE, "lab")


def test_sensor_ids_depend_on_zone_and_metric():
    z = zone_id(DEFAULT_HABITAT_CODE, "lab")
    assert sensor_id(z, "co2_mmhg") == sensor_id(z, "co2_mmhg")
    assert sensor_id(z, "co2_mmhg") != sensor_id(z, "o2_pct")
