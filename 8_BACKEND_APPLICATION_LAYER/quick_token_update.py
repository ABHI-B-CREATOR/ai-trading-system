"""
Quick script to update access token using existing request_token
"""
from kiteconnect import KiteConnect
import yaml

# Your credentials
API_KEY = "o666qh3obb8lvwla"
REQUEST_TOKEN = "IRCaQIweCsuTKpNu5OOiB2fP2puIRTm8"

# Get API Secret from user
print("=" * 50)
print("ZERODHA ACCESS TOKEN GENERATOR")
print("=" * 50)
print(f"\nAPI Key: {API_KEY}")
print(f"Request Token: {REQUEST_TOKEN}")
print()

api_secret = input("Enter your Zerodha API Secret: ").strip()

if not api_secret:
    print("❌ API Secret is required!")
    exit(1)

try:
    kite = KiteConnect(api_key=API_KEY)
    data = kite.generate_session(REQUEST_TOKEN, api_secret=api_secret)
    access_token = data["access_token"]
    
    print(f"\n✅ SUCCESS!")
    print(f"New Access Token: {access_token}")
    
    # Update backend_settings.yaml
    settings_path = "backend_settings.yaml"
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = yaml.safe_load(f)
        
        settings["zerodha_access_token"] = access_token
        
        with open(settings_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(settings, f, sort_keys=False)
        
        print(f"\n✅ Updated {settings_path} with new token!")
        print("\n🔄 Now restart your backend to use the new token.")
        
    except Exception as e:
        print(f"\n⚠️ Could not update settings file: {e}")
        print(f"Please manually update zerodha_access_token in backend_settings.yaml")
        print(f"New token: {access_token}")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nPossible issues:")
    print("1. Request token already used (each token works only once)")
    print("2. Request token expired (valid for ~2 minutes)")
    print("3. Wrong API secret")
    print("\nSolution: Login again to Zerodha to get a fresh request_token")
