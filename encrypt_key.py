from cryptography.fernet import Fernet

# 1. Generate and save a key (Keep this secret!)
# In a real app, you should save this key securely and reuse it.
key = b'bS-JtNYvy4uYwAg3DI1E4TqagEfQgJVY2y5p7jgcizA='.strip()
print(f"Hash Key = {key}")
cipher_suite = Fernet(key)

# 2. Define the string to encrypt
original_text = "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"

# 3. Encrypt the string
# The string must be converted to bytes using .encode() first
byte_text = original_text.encode()
encrypted_text = cipher_suite.encrypt(byte_text)

print(f"Original: {original_text}")
print(f"Encrypted: {encrypted_text.decode()}") # Decoding just to print it cleanly

# 4. Decrypt the string
decrypted_bytes = cipher_suite.decrypt(encrypted_text)
decrypted_text = decrypted_bytes.decode()

print(f"Decrypted: {decrypted_text}")
