from qsim.entities.pauli_frame import PauliFrameToken


def test_pauli_frame_token_holds_fields():
    token = PauliFrameToken(token_id="pft-1", created_at=3.5)
    assert token.token_id == "pft-1"
    assert token.created_at == 3.5


def test_pauli_frame_tokens_with_equal_fields_are_equal():
    a = PauliFrameToken(token_id="pft-1", created_at=3.5)
    b = PauliFrameToken(token_id="pft-1", created_at=3.5)
    assert a == b


def test_pauli_frame_tokens_with_different_ids_are_not_equal():
    a = PauliFrameToken(token_id="pft-1", created_at=3.5)
    b = PauliFrameToken(token_id="pft-2", created_at=3.5)
    assert a != b
