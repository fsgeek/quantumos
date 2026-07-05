import dataclasses

import pytest

from qsim.entities.module import Module, PathId, PortId, make_path_id


def test_portid_is_frozen():
    port = PortId(module_id="mod-a", port_index=0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        port.port_index = 1  # type: ignore[misc]


def test_portid_is_hashable_and_usable_in_sets():
    a = PortId("mod-a", 0)
    b = PortId("mod-a", 0)
    c = PortId("mod-a", 1)
    assert a == b
    assert {a, b, c} == {a, c}


def test_module_holds_ports_tuple():
    p0 = PortId("mod-a", 0)
    p1 = PortId("mod-a", 1)
    module = Module(module_id="mod-a", ports=(p0, p1))
    assert module.module_id == "mod-a"
    assert module.ports == (p0, p1)


def test_make_path_id_is_symmetric_and_canonically_ordered():
    a = PortId("mod-a", 0)
    b = PortId("mod-b", 1)
    assert make_path_id(a, b) == make_path_id(b, a)
    assert make_path_id(a, b) == (a, b)  # "mod-a" < "mod-b"


def test_make_path_id_usable_as_dict_key_regardless_of_argument_order():
    a = PortId("mod-a", 0)
    b = PortId("mod-b", 1)
    table: dict[PathId, str] = {make_path_id(a, b): "reservation-1"}
    assert table[make_path_id(b, a)] == "reservation-1"
