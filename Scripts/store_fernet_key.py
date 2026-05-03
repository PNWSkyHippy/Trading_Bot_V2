"""
store_fernet_key.py
====================
One-time script to store the Fernet BASE_KEY in Windows Credential Manager.
Run this ONCE then delete or keep — the key is safely stored in Windows vault.

Usage:
    python Scripts\store_fernet_key.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import keyring

# Paste your BASE_KEY here between the quotes
BASE_KEY = "bS-JtNYvy4uYwAg3DI1E4TqagEfQgJVY2y5p7jgcizA="

keyring.set_password("trading_bot_v2", "fernet_key", BASE_KEY)

# Verify it stored correctly
stored = keyring.get_password("trading_bot_v2", "fernet_key")
if stored == BASE_KEY:
    print("✅ Fernet key stored successfully in Windows Credential Manager")
    print("   You can now remove BASE_KEY from config.py")
    print("   Key is stored securely in: Control Panel > Credential Manager > Windows Credentials")
else:
    print("❌ Storage failed — key does not match")
