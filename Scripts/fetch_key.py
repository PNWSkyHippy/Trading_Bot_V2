import os
API_KEY2    = os.getenv("TRADER-DEV-APII-KEY")
print(f"API key configured: {'yes' if API_KEY2 else 'no'}")
