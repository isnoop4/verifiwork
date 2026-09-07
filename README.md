# VerifiWork

> A micro-task marketplace (starting with audio transcription) where work quality is judged by an AI validator against a public rubric, and payment releases automatically from escrow — built for **GenLayer Agent Tank**, Future of Work track.

## Problem

Gig platform data-workers (transcription, AI evaluation, annotation) face:
- Subjective quality reviews from a single reviewer
- Slow, opaque payment disputes
- Reputation locked into a single platform

## Solution

An Intelligent Contract on GenLayer that runs the full work cycle end-to-end:

1. **Requester** posts a task + public quality rubric + reward (native GEN), funds go into on-chain escrow
2. **Worker** submits their work
3. **AI validator committee** (via GenLayer's Equivalence Principle) judges the submission against the rubric defined in the contract code
4. If **APPROVED** → reward is automatically released to the worker
5. If **REJECTED** → funds are automatically refunded to the requester

## Status

✅ The `TranscriptionEscrow` contract has been tested end-to-end on GenLayer Studio:
- `create_task` → `submit_result` → `evaluate_and_release`
- Both scenarios verified: REJECTED (poor transcript, refund to requester) and APPROVED (good transcript, payout to worker)

## Technical Architecture

See [`contracts/transcription_escrow.py`](contracts/transcription_escrow.py).

**Main state:** `requester`, `worker`, `reward`, `audio_url`, `rubric`, `transcript`, `status`, `verdict_reason`

**Functions:**
| Function | Type | Description |
|---|---|---|
| `create_task(audio_url, rubric)` | write, payable | Requester creates the task, sends reward via `gl.message.value` |
| `submit_result(transcript_text)` | write | Worker submits their work |
| `evaluate_and_release()` | write | AI validator judges the transcript against the rubric (`gl.eq_principle.prompt_non_comparative`), then auto payout/refund via `gl.get_contract_at().emit_transfer()` |
| `dispute()` | write | Appeal placeholder (not fully implemented yet) |
| `get_status()`, `get_reward()`, `get_verdict_reason()`, `get_task_details()` | view | Read task status |

**Risk mitigations:**
- Worker input is wrapped as `DATA_ONLY_NOT_INSTRUCTIONS` in the evaluation prompt to mitigate prompt injection
- The evaluation output is extracted as JSON from the raw model output (robust against models that prepend a reasoning/`<think>` block before the JSON)
- The rubric only includes criteria verifiable from the transcript text alone (not a direct comparison against the original audio)

## How to Try It

1. Deploy `contracts/transcription_escrow.py` on [GenLayer Studio](https://studio.genlayer.com)
2. Call `create_task` with `audio_url`, `rubric`, and send GEN value as the reward
3. Call `submit_result` with the transcript text
4. Call `evaluate_and_release` — the AI validator will judge it and release funds automatically
5. Check `get_status()` and `get_verdict_reason()` to see the result

## Limitations (MVP)

- Only supports 1 active task per contract instance (no multi-task support yet)
- `dispute()` is still a placeholder, doesn't yet trigger re-evaluation by a larger committee
- The rubric can't yet verify the transcript against the original audio (validators only receive text)
- No separate reputation tracker yet (planned for future development)

## Roadmap

- A separate `ReputationTracker` contract for worker historical scores (portable across platforms)
- Multi-task support per contract (task registry)
- Full appeal path with a larger committee

## Track

Future of Work — GenLayer Agent Tank
