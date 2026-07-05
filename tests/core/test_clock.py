import pytest

from qsim.core.clock import SimClock


def test_new_clock_starts_at_zero():
    clock = SimClock()
    assert clock.now() == 0.0


def test_advance_to_moves_time_forward():
    clock = SimClock()
    clock.advance_to(5.0)
    assert clock.now() == 5.0


def test_advance_to_same_time_is_allowed():
    clock = SimClock()
    clock.advance_to(3.0)
    clock.advance_to(3.0)
    assert clock.now() == 3.0


def test_advance_to_backward_raises_value_error():
    clock = SimClock()
    clock.advance_to(10.0)
    with pytest.raises(ValueError):
        clock.advance_to(9.999)
    assert clock.now() == 10.0  # rejected advance must not mutate state
