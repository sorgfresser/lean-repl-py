from lean_repl_py import LeanREPLProofState, LeanREPLNextProofState


def test_send_command(handler):
    handler.send_command("def f := 2")
    result_dict, env = handler.receive_json()
    assert not result_dict
    assert env.env_index == 0


def test_prove(handler):
    handler.send_command("theorem test : 1 = 1 := by sorry")
    result_dict, env = handler.receive_json()
    proof_state = result_dict["sorries"][0]
    assert isinstance(proof_state, LeanREPLProofState)
    assert proof_state.proof_state == 0
    assert proof_state.goal == "⊢ 1 = 1"

    handler.send_tactic("rfl", proof_state.proof_state)
    result_proof_state, env = handler.receive_json()
    assert isinstance(result_proof_state, LeanREPLNextProofState)
    assert len(result_proof_state.goals) == 0


def test_prove_extended(handler):
    handler.send_command(
        "theorem test_extended (p q : Prop) (hp : p) (hq : q) : p ∧ q := by sorry"
    )
    result_dict, env = handler.receive_json()
    proof_state = result_dict["sorries"][0]
    assert isinstance(proof_state, LeanREPLProofState)
    assert proof_state.proof_state == 0
    assert proof_state.goal == "p q : Prop\nhp : p\nhq : q\n⊢ p ∧ q"

    handler.send_tactic("constructor", proof_state.proof_state)
    result_proof_state, env = handler.receive_json()
    assert isinstance(result_proof_state, LeanREPLNextProofState)
    assert len(result_proof_state.goals) == 2
    assert result_proof_state.goals[0] == "case left\np q : Prop\nhp : p\nhq : q\n⊢ p"
    assert result_proof_state.goals[1] == "case right\np q : Prop\nhp : p\nhq : q\n⊢ q"
    proof_state_idx = result_proof_state.proof_state
    assert proof_state_idx == 1

    handler.send_tactic("exact hp", proof_state_idx)
    result_proof_state, env = handler.receive_json()
    assert isinstance(result_proof_state, LeanREPLNextProofState)
    assert len(result_proof_state.goals) == 1
    assert result_proof_state.goals[0] == "case right\np q : Prop\nhp : p\nhq : q\n⊢ q"
    proof_state_idx = result_proof_state.proof_state
    assert proof_state_idx == 2

    handler.send_tactic("exact hq", proof_state_idx)
    result_proof_state, env = handler.receive_json()
    assert isinstance(result_proof_state, LeanREPLNextProofState)
    assert len(result_proof_state.goals) == 0
