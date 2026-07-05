from qsim.observe.work_accounting import WorkAccounting


def test_defaults_are_all_zero():
    wa = WorkAccounting()
    assert wa.offered == 0
    assert wa.retries == 0
    assert wa.admitted == 0
    assert wa.deferred == 0
    assert wa.dropped == 0
    assert wa.completed_in_deadline == 0
    assert wa.completed_late == 0
    assert wa.failed == 0
    assert wa.pool_returned == 0


def test_attempts_is_offered_plus_retries():
    wa = WorkAccounting(offered=10, retries=4)
    assert wa.attempts() == 14


def test_goodput_is_completed_in_deadline_over_offered():
    wa = WorkAccounting(offered=8, completed_in_deadline=2)
    assert wa.goodput() == 0.25


def test_goodput_is_zero_when_no_work_offered():
    wa = WorkAccounting(offered=0, completed_in_deadline=0)
    assert wa.goodput() == 0.0


def test_pool_returned_is_tracked_separately_from_completed():
    wa = WorkAccounting(offered=5, completed_in_deadline=1, pool_returned=3)
    assert wa.goodput() == 0.2
    assert wa.pool_returned == 3
