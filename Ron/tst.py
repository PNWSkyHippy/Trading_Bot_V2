import os

import kagglehub
import torch
from transformers import AutoProcessor, AutoModelForCausalLM


MODEL_HANDLE = os.getenv("KAGGLE_MODEL_HANDLE", "google/gemma-4/transformers/gemma-4-12b")

print(f"Downloading model: {MODEL_HANDLE}")
MODEL_PATH = kagglehub.model_download(MODEL_HANDLE)
print(f"Model path: {MODEL_PATH}")

has_cuda = torch.cuda.is_available()
print(f"torch={torch.__version__} cuda_available={has_cuda} cuda_version={torch.version.cuda}")

if not has_cuda and "12b" in MODEL_HANDLE.lower():
    raise RuntimeError(
        "This environment is CPU-only, and gemma-4-12b is too heavy/unstable here. "
        "Use a smaller model handle via KAGGLE_MODEL_HANDLE or run on a CUDA GPU."
    )

processor = AutoProcessor.from_pretrained(MODEL_PATH)

dtype = torch.float16 if has_cuda else torch.float32
device_map = "auto" if has_cuda else {"": "cpu"}

model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=dtype,
    device_map=device_map,
    low_cpu_mem_usage=True,
)

print("Model loaded successfully.")
