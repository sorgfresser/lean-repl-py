import gc

from lean_repl_py import (
    LeanREPLProofState,
    LeanREPLNextProofState,
    LeanREPLAsyncHandler,
)
import pytest


@pytest.mark.asyncio(loop_scope="function")
async def test_send_command(async_handler):
    await async_handler.send_command("def f := 2")
    result_dict, env = await async_handler.receive_json()
    assert not result_dict
    assert env.env_index == 0


@pytest.mark.asyncio(loop_scope="function")
async def test_prove(async_handler):
    await async_handler.send_command("theorem test : 1 = 1 := by sorry")
    result_dict, env = await async_handler.receive_json()
    proof_state = result_dict["sorries"][0]
    assert isinstance(proof_state, LeanREPLProofState)
    assert proof_state.proof_state == 0
    assert proof_state.goal == "⊢ 1 = 1"

    await async_handler.send_tactic("rfl", proof_state.proof_state)
    result_proof_state, env = await async_handler.receive_json()
    assert isinstance(result_proof_state, LeanREPLNextProofState)
    assert len(result_proof_state.goals) == 0


@pytest.mark.asyncio(loop_scope="function")
async def test_prove_extended(async_handler):
    await async_handler.send_command(
        "theorem test_extended (p q : Prop) (hp : p) (hq : q) : p ∧ q := by sorry"
    )
    result_dict, env = await async_handler.receive_json()
    proof_state = result_dict["sorries"][0]
    assert isinstance(proof_state, LeanREPLProofState)
    assert proof_state.proof_state == 0
    assert proof_state.goal == "p q : Prop\nhp : p\nhq : q\n⊢ p ∧ q"

    await async_handler.send_tactic("constructor", proof_state.proof_state)
    result_proof_state, env = await async_handler.receive_json()
    assert isinstance(result_proof_state, LeanREPLNextProofState)
    assert len(result_proof_state.goals) == 2
    assert result_proof_state.goals[0] == "case left\np q : Prop\nhp : p\nhq : q\n⊢ p"
    assert result_proof_state.goals[1] == "case right\np q : Prop\nhp : p\nhq : q\n⊢ q"
    proof_state_idx = result_proof_state.proof_state
    assert proof_state_idx == 1

    await async_handler.send_tactic("exact hp", proof_state_idx)
    result_proof_state, env = await async_handler.receive_json()
    assert isinstance(result_proof_state, LeanREPLNextProofState)
    assert len(result_proof_state.goals) == 1
    assert result_proof_state.goals[0] == "case right\np q : Prop\nhp : p\nhq : q\n⊢ q"
    proof_state_idx = result_proof_state.proof_state
    assert proof_state_idx == 2

    await async_handler.send_tactic("exact hq", proof_state_idx)
    result_proof_state, env = await async_handler.receive_json()
    assert isinstance(result_proof_state, LeanREPLNextProofState)
    assert len(result_proof_state.goals) == 0


@pytest.mark.asyncio(loop_scope="function")
async def test_destructor():
    curr_handler = LeanREPLAsyncHandler()
    await curr_handler.await_process()
    with pytest.warns(ResourceWarning):
        del curr_handler
    gc.collect()
