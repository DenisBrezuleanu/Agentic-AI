# Lab 3 - Checkpoint notes

## Exercise 1

1. A typical correct example has four LLM rounds but multiple tool calls: list hosts (1), installed packages of production hosts (3), package CVE lookup (up to 9), final answer (no tools). Multiple calls in the same model turn can be batched, so 13 tool calls do not require 13 model round trips.
2. Each model call resends system instructions, the original question, past model tool calls and tool response messages. This explains growing context/token use.
3. OpenSSH CVE-2024-6387 is below the stated CVSS >= 9.0 cutoff; do not include it in the list of critical exposures for this question.

## Exercise 2

1. On denial, the tool response includes the human operator's feedback; the model should obey that feedback in the next tool proposal.
2. Whether an injected comment survived must be verified by inspecting the actual produced diff. The model and a human reviewer, not just a sandbox, are responsible for identifying malicious content in a file.
3. Prompt injection controls are not a substitute for path enforcement. Sandbox tests check that traversals and symlink escapes are blocked regardless of model behavior.
4. A destination file for a new write does not exist yet, so canonicalizing the entire destination path may fail. Resolve/check parent components and prevent lexical traversal; check symlinks when existing parents are traversed.

## Exercise 3

A worker returns compact structured findings rather than the entire raw log. This prevents the orchestrator from repeatedly paying for all log tokens at each later step. Grand total may decrease even after counting the extra worker call, depending on the number of orchestration steps and the worker's summarized response length. Exact token measurements require a real model run.

The sub-agent must not claim success after a failed run, and its supporting evidence should match actual source log lines. It is still possible for the worker to miss events, so checking evidence and inexpensive deterministic indicators improves reliability.

| Mode | Orchestrator input tokens/step | Orchestrator total | Worker total | Grand total |
|---|---|---|---|---|
| single | pending live run | pending | 0 | pending |
| orchestrator | pending live run | pending | pending | pending |
| subagent (stretch) | pending live run | pending | pending | pending |

Commands from `agent-lab3/`:

```bash
python lab3_ex1_react.py
python lab3_ex2_hitl.py
python lab3_ex3_orchestrator.py single --auto-approve
python lab3_ex3_orchestrator.py orchestrator --auto-approve
python lab3_ex3_orchestrator.py subagent --auto-approve
python -m pytest -q
```
