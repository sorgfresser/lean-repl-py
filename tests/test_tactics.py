from lean_repl_py import LeanREPLHandler, LeanREPLProofState, LeanREPLNextProofState


def test_optional_message(handler: LeanREPLHandler):
    theorem = """theorem falsify (h: False) : False := by sorry"""
    handler.send_command(theorem)
    response, env = handler.receive_json()
    sorries = response["sorries"]
    assert len(sorries) == 1
    state = sorries[0]
    assert isinstance(state, LeanREPLProofState)
    handler.send_tactic("exact?", state.proof_state)
    response, env = handler.receive_json()
    assert isinstance(response, LeanREPLNextProofState)
    assert response.messages
