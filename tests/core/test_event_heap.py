from qsim.core.event_heap import EventHeap, HeapEntry


def test_push_returns_sequential_seq_starting_at_zero():
    heap = EventHeap()
    assert heap.push(1.0, "a") == 0
    assert heap.push(2.0, "b") == 1
    assert heap.push(1.0, "c") == 2


def test_len_tracks_pending_entries():
    heap = EventHeap()
    assert len(heap) == 0
    heap.push(1.0, "a")
    heap.push(2.0, "b")
    assert len(heap) == 2
    heap.pop()
    assert len(heap) == 1


def test_pop_on_empty_heap_returns_none():
    heap = EventHeap()
    assert heap.pop() is None


def test_pop_returns_earliest_time_first():
    heap = EventHeap()
    heap.push(5.0, "later")
    heap.push(1.0, "earlier")
    heap.push(3.0, "middle")

    order = [heap.pop().payload for _ in range(3)]
    assert order == ["earlier", "middle", "later"]


def test_equal_time_events_tiebreak_by_seq_in_push_order():
    heap = EventHeap()
    heap.push(2.0, "second-pushed-later-time")
    seq_first = heap.push(1.0, "first-pushed-at-t1")
    seq_second = heap.push(1.0, "second-pushed-at-t1")
    assert seq_first < seq_second

    first = heap.pop()
    second = heap.pop()
    assert (first.time, first.payload) == (1.0, "first-pushed-at-t1")
    assert (second.time, second.payload) == (1.0, "second-pushed-at-t1")


def test_equal_time_tiebreak_is_independent_of_heap_internal_order():
    heap = EventHeap()
    seqs_and_payloads = []
    for payload in ["d", "b", "a", "c"]:
        seq = heap.push(9.0, payload)
        seqs_and_payloads.append((seq, payload))
    expected_order = [p for _, p in sorted(seqs_and_payloads)]

    popped = [heap.pop().payload for _ in range(4)]
    assert popped == expected_order


def test_heap_entry_orders_by_time_then_seq_ignoring_payload():
    a = HeapEntry(time=1.0, seq=0, payload={"unorderable": object()})
    b = HeapEntry(time=1.0, seq=1, payload={"unorderable": object()})
    c = HeapEntry(time=0.5, seq=5, payload=None)
    assert a < b
    assert c < a
