from lean_repl_py import LeanREPLHandler, LeanREPLProofState, LeanREPLNextProofState


def test_optional_message(handler: LeanREPLHandler):
    theorem = """theorem conjecture_commutative_property__ (X : Type) [Mul X] 
(h : ∀ x y : X, (x * y) * x = y) 
(a b : X) : a * (b * a) = b :=  by sorry"""
    handler.send_command(theorem)
    response, env = handler.receive_json()
    sorries = response["sorries"]
    assert len(sorries) == 1
    state = sorries[0]
    assert isinstance(state, LeanREPLProofState)
    handler.send_tactic("specialize h a b", state.proof_state)
    response, env = handler.receive_json()
    assert isinstance(response, LeanREPLNextProofState)
    handler.send_tactic("rw[← h]", response.proof_state)
    response, env = handler.receive_json()
    assert isinstance(response, LeanREPLNextProofState)
    handler.send_tactic("apply?", response.proof_state)
    response, env = handler.receive_json()
    assert isinstance(response, LeanREPLNextProofState)
    assert response.messages
