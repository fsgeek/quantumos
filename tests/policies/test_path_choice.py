"""B1: PathChoice strategy unit tests (design spec §2 'path allocation as
separable mechanisms'; prereg B1 behavior-preserving mandate)."""
import pytest

from qsim.entities import PortId, make_path_id
from qsim.policies.path_choice import (
    BestHeraldingPathChoice,
    PathChoice,
    RoundRobinPathChoice,
)


def _ports(n: int) -> list[PortId]:
    return [PortId(module_id=f"M{i}", port_index=0) for i in range(n)]


def _choose(chooser, ports, *, round_id="R1", lease_ordinal=0,
            taken_path_ids=frozenset(), heralding_p_by_path=None):
    return chooser.choose_endpoints(
        round_id=round_id,
        lease_ordinal=lease_ordinal,
        ports=ports,
        taken_path_ids=taken_path_ids,
        heralding_p_by_path=heralding_p_by_path or {},
    )


def test_round_robin_first_call_returns_first_adjacent_pair_in_raw_order():
    ports = _ports(4)
    chooser = RoundRobinPathChoice()
    assert _choose(chooser, ports) == (ports[0], ports[1])


def test_round_robin_second_call_advances_the_counter():
    ports = _ports(4)
    chooser = RoundRobinPathChoice()
    _choose(chooser, ports)
    assert _choose(chooser, ports) == (ports[1], ports[2])


def test_round_robin_wrap_call_returns_raw_not_canonical_order():
    # At idx = n-1 the raw pair is (M3, M0) — the REVERSE of canonical PathId
    # order. Raw order is load-bearing: the herald draw key embeds
    # lease.endpoints in this order and qubit_handles take module_id from
    # endpoint a, so canonicalizing here would silently change trace bytes.
    ports = _ports(4)
    chooser = RoundRobinPathChoice()
    for _ in range(3):
        _choose(chooser, ports)
    assert _choose(chooser, ports) == (ports[3], ports[0])


def test_round_robin_returns_the_exact_portid_objects_from_the_ports_sequence():
    ports = _ports(4)
    chooser = RoundRobinPathChoice()
    a, b = _choose(chooser, ports)
    assert a is ports[0]
    assert b is ports[1]


def test_round_robin_ignores_every_contextual_argument():
    # _endpoints_for ignored its round_id/ordinal arguments; the transplanted
    # chooser must too — varying context must not perturb the sequence.
    ports = _ports(4)
    chooser = RoundRobinPathChoice()
    seq = [
        _choose(chooser, ports, round_id="R1", lease_ordinal=0),
        _choose(chooser, ports, round_id="R9", lease_ordinal=7,
                taken_path_ids=frozenset({make_path_id(ports[0], ports[1])}),
                heralding_p_by_path={make_path_id(ports[2], ports[3]): 1.0}),
        _choose(chooser, ports, round_id="R2", lease_ordinal=1),
    ]
    assert seq == [(ports[0], ports[1]), (ports[1], ports[2]), (ports[2], ports[3])]


def test_round_robin_counter_is_per_instance():
    ports = _ports(4)
    chooser_a = RoundRobinPathChoice()
    chooser_b = RoundRobinPathChoice()
    _choose(chooser_a, ports)
    _choose(chooser_a, ports)
    # A fresh instance starts from 0 regardless of the other's progress.
    assert _choose(chooser_b, ports) == (ports[0], ports[1])


def test_round_robin_satisfies_the_path_choice_protocol():
    assert isinstance(RoundRobinPathChoice(), PathChoice)


def test_best_heralding_picks_the_argmax_p_enumerated_path():
    ports = _ports(4)
    table = {
        make_path_id(ports[0], ports[1]): 0.3,
        make_path_id(ports[1], ports[2]): 0.9,
        make_path_id(ports[2], ports[3]): 0.6,
    }
    chosen = _choose(BestHeraldingPathChoice(), ports, heralding_p_by_path=table)
    assert chosen == make_path_id(ports[1], ports[2])


def test_best_heralding_excludes_paths_already_taken_within_the_round():
    ports = _ports(4)
    best = make_path_id(ports[1], ports[2])
    second_best = make_path_id(ports[2], ports[3])
    table = {
        make_path_id(ports[0], ports[1]): 0.3,
        best: 0.9,
        second_best: 0.6,
    }
    chosen = _choose(BestHeraldingPathChoice(), ports,
                     taken_path_ids=frozenset({best}),
                     heralding_p_by_path=table)
    assert chosen == second_best


def test_best_heralding_excludes_table_paths_outside_the_port_universe():
    # A calibrated path whose endpoints the fabric does not synthesize can
    # never be reserved — it must not be a candidate, however good its p.
    ports = _ports(2)
    foreign = make_path_id(PortId("M8", 0), PortId("M9", 0))
    local = make_path_id(ports[0], ports[1])
    table = {foreign: 1.0, local: 0.2}
    chosen = _choose(BestHeraldingPathChoice(), ports, heralding_p_by_path=table)
    assert chosen == local


def test_best_heralding_breaks_ties_to_the_lexicographically_least_canonical_path():
    ports = _ports(4)
    table = {
        make_path_id(ports[2], ports[3]): 0.7,
        make_path_id(ports[0], ports[1]): 0.7,
        make_path_id(ports[1], ports[2]): 0.7,
    }
    chosen = _choose(BestHeraldingPathChoice(), ports, heralding_p_by_path=table)
    assert chosen == make_path_id(ports[0], ports[1])


def test_best_heralding_returns_endpoints_in_canonical_path_id_order():
    ports = _ports(2)
    # Build the table key from the reversed pair; make_path_id canonicalizes,
    # and the chooser must return that canonical order (the PathId itself).
    path = make_path_id(ports[1], ports[0])
    chosen = _choose(BestHeraldingPathChoice(), ports,
                     heralding_p_by_path={path: 0.5})
    assert chosen == (ports[0], ports[1])


def test_best_heralding_raises_value_error_naming_the_round_on_exhaustion():
    ports = _ports(4)
    only = make_path_id(ports[0], ports[1])
    with pytest.raises(ValueError, match="R7"):
        _choose(BestHeraldingPathChoice(), ports,
                round_id="R7", lease_ordinal=1,
                taken_path_ids=frozenset({only}),
                heralding_p_by_path={only: 0.9})


def test_best_heralding_raises_on_an_empty_table():
    ports = _ports(4)
    with pytest.raises(ValueError, match="R3"):
        _choose(BestHeraldingPathChoice(), ports, round_id="R3",
                heralding_p_by_path={})


def test_best_heralding_is_deterministic_and_stateless_across_instances():
    ports = _ports(4)
    table = {
        make_path_id(ports[0], ports[1]): 0.3,
        make_path_id(ports[1], ports[2]): 0.9,
    }
    a = BestHeraldingPathChoice()
    b = BestHeraldingPathChoice()
    first = _choose(a, ports, heralding_p_by_path=table)
    # Repeated calls on ONE instance with identical inputs repeat the choice
    # (no hidden counter), and a fresh instance agrees (no per-instance state).
    assert _choose(a, ports, heralding_p_by_path=table) == first
    assert _choose(b, ports, heralding_p_by_path=table) == first


def test_best_heralding_satisfies_the_path_choice_protocol():
    assert isinstance(BestHeraldingPathChoice(), PathChoice)
