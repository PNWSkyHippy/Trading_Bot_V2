import time
import pyotp
import qrcode

def setup_2fa():
    # 1. Generate a random base32 secret key
    secret = pyotp.random_base32()
    print(f"Your Secret Key: {secret}")
    
    # 2. Create the provisioning URI used by authenticator apps
    # Replace 'MyApp' and 'user@example.com' with your project/user identifiers
    totp_auth_url = pyotp.totp.TOTP(secret).provisioning_uri(
        name="ronkhensley@gmail.com", 
        issuer_name="TestApp"
    )
    
    # 3. Generate and display a terminal-friendly QR code
    print("\nScan this QR code with your Authenticator App:")
    qr = qrcode.QRCode(version=1, box_size=1, border=2)
    qr.add_data(totp_auth_url)
    qr.make(fit=True)
    
    # print_tty=True displays the QR code using inverse block colors inside the terminal
    qr.print_tty()
    
    return secret

def verify_2fa(secret):
    totp = pyotp.totp.TOTP(secret)
    
    print("\n--- 2FA Verification Mode ---")
    while True:
        token = input("Enter the 6-digit code from your app (or 'q' to quit): ").strip()
        if token.lower() == 'q':
            break
            
        # Verify the entered token
        if totp.verify(token):
            print("\033[92mSuccess: Code is valid!\033[0m")
            break
        else:
            print("\033[91mInvalid code. Please try again.\033[0m")

if __name__ == "__main__":
    print("=== Initial 2FA Setup ===")
    user_secret = setup_2fa()
    
    # Small pause to allow the user to look at the setup instructions
    input("\nPress Enter once you have added the account to your app...")
    
    # Test the verification flow
    verify_2fa(user_secret)
