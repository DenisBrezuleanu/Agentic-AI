# Lab 2 - Model literacy

1. VRAM for a 70B model at 4-bit: 70 * (4/8) * 1.2 = **42 GB**. A 24 GB GPU cannot hold the full model at that approximation; offloading or additional GPUs would be needed.
2. Choose `mistralai/Mistral-7B-Instruct-v0.3`, not the base checkpoint. Instruct/chat fine-tuning improves instruction following and structured tool-call compliance, but every tool response still needs code validation.

## Demonstration commands

```bash
python smoke_test.py
python module1_prompting.py
python module2_structured.py
python module3_tools.py
python bonus_react.py
python homework_david_vs_goliath.py
python homework_david_vs_goliath.py gemini-3.5-flash-lite
python homework_david_vs_goliath.py --compare --runs 3
python -m pytest -q
```

The first commands need an API key. Local homework needs Ollama with `qwen2.5:1.5b`; the cloud comparison needs a Gemini key.
