# Gemma Working Prompts

## Colab setup

```python
!pip -q install -U transformers accelerate sentencepiece torch
```

```python
import torch
print("Torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
```

## Login if needed

```python
!pip -q install -U huggingface_hub
from huggingface_hub import notebook_login
notebook_login()
```

## Load Gemma

```python
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = "google/gemma-2-2b-it"
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto"
)
```

## Quick chat test

```python
messages = [{"role": "user", "content": "Who are you?"}]
inputs = tokenizer.apply_chat_template(
    messages,
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
).to(model.device)

outputs = model.generate(**inputs, max_new_tokens=40)
print(tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True))
```

## Reusable helper

```python
def ask_gemma(prompt, max_new_tokens=180, temperature=0.7):
    messages = [{"role": "user", "content": prompt}]
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=temperature,
        top_p=0.95,
    )
    return tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
```

## Clean trading prompt

```text
Here are 3 trading risk rules, focusing on a balanced approach:

1. Risk as a percentage of capital:
- Never risk more than 1% to 2% of your total capital on a single trade.
- This helps limit damage from any one loss and keeps your account alive through losing streaks.

2. Set a stop loss before entering:
- Always define the exit point before you buy.
- A trade without a stop loss can turn a small mistake into a large loss.

3. Keep reward bigger than risk:
- Aim for at least 2x reward for every 1x risk.
- This way, you do not need to be right all the time to stay profitable.
```