import pytest

from qsim.entities.decoder import DecoderJob


def make_job() -> DecoderJob:
    return DecoderJob(job_id="job-1", round_id="round-1", priority=0, enqueue_time=0.0)


def test_decoder_job_starts_enqueued_only():
    job = make_job()
    assert job.dequeue_time is None
    assert job.completion_time is None
    assert job.cancelled_at is None


def test_dequeue_sets_time():
    job = make_job()
    job.dequeue(at=1.0)
    assert job.dequeue_time == 1.0


def test_dequeue_twice_raises():
    job = make_job()
    job.dequeue(at=1.0)
    with pytest.raises(ValueError):
        job.dequeue(at=2.0)


def test_complete_requires_dequeue_first():
    job = make_job()
    with pytest.raises(ValueError):
        job.complete(at=2.0)


def test_complete_after_dequeue_succeeds():
    job = make_job()
    job.dequeue(at=1.0)
    job.complete(at=2.0)
    assert job.completion_time == 2.0


def test_complete_twice_raises():
    job = make_job()
    job.dequeue(at=1.0)
    job.complete(at=2.0)
    with pytest.raises(ValueError):
        job.complete(at=3.0)


def test_cancel_before_dequeue_succeeds():
    job = make_job()
    job.cancel(at=1.0)
    assert job.cancelled_at == 1.0


def test_cancel_after_completion_raises():
    job = make_job()
    job.dequeue(at=1.0)
    job.complete(at=2.0)
    with pytest.raises(ValueError):
        job.cancel(at=3.0)


def test_cancel_twice_raises():
    job = make_job()
    job.cancel(at=1.0)
    with pytest.raises(ValueError):
        job.cancel(at=2.0)


def test_complete_after_cancel_raises():
    job = make_job()
    job.dequeue(at=1.0)
    job.cancel(at=2.0)
    with pytest.raises(ValueError):
        job.complete(at=3.0)


def test_dequeue_after_cancel_raises():
    job = make_job()
    job.cancel(at=1.0)
    with pytest.raises(ValueError):
        job.dequeue(at=2.0)
