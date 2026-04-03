"""
Zerodha Connection Diagnostic & Fix Script
Tests API connection, token validity, and WebSocket connection
"""
import sys
import time
import threading
from datetime import datetime

# Add parent path for imports
sys.path.insert(0, ".")

try:
    from kiteconnect import KiteConnect, KiteTicker
    import yaml
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Run: pip install kiteconnect pyyaml")
    sys.exit(1)

def load_settings():
    """Load settings from yaml file"""
    try:
        with open("backend_settings.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Cannot load settings: {e}")
        return None

def test_api_connection(api_key, access_token):
    """Test basic API connection"""
    print("\n" + "="*50)
    print("TEST 1: API Connection")
    print("="*50)
    
    try:
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)
        
        # Try to get profile - this validates the token
        profile = kite.profile()
        print(f"✅ API Connection: SUCCESS")
        print(f"   User: {profile.get('user_name', 'Unknown')}")
        print(f"   Email: {profile.get('email', 'Unknown')}")
        print(f"   User Type: {profile.get('user_type', 'Unknown')}")
        return True, kite
        
    except Exception as e:
        error_msg = str(e).lower()
        print(f"❌ API Connection: FAILED")
        print(f"   Error: {e}")
        
        if "token" in error_msg or "session" in error_msg or "invalid" in error_msg:
            print("\n🔧 DIAGNOSIS: Access token is INVALID or EXPIRED")
            print("   → You need to generate a NEW access token")
            return False, None
        elif "network" in error_msg:
            print("\n🔧 DIAGNOSIS: Network connectivity issue")
            return False, None
        else:
            print("\n🔧 DIAGNOSIS: Unknown error")
            return False, None

def test_websocket_connection(api_key, access_token):
    """Test WebSocket connection"""
    print("\n" + "="*50)
    print("TEST 2: WebSocket Connection")
    print("="*50)
    
    result = {"connected": False, "error": None, "ticks_received": 0}
    test_complete = threading.Event()
    
    def on_connect(ws, response):
        print(f"✅ WebSocket Connected!")
        result["connected"] = True
        # Subscribe to NIFTY 50 index
        ws.subscribe([256265])  # NIFTY 50 token
        ws.set_mode(ws.MODE_LTP, [256265])
        print(f"   Subscribed to NIFTY (token: 256265)")
    
    def on_ticks(ws, ticks):
        result["ticks_received"] += 1
        if result["ticks_received"] == 1:
            print(f"✅ Receiving live ticks!")
            if ticks:
                tick = ticks[0]
                print(f"   NIFTY LTP: ₹{tick.get('last_price', 'N/A')}")
        if result["ticks_received"] >= 3:
            test_complete.set()
    
    def on_close(ws, code, reason):
        print(f"⚠️ WebSocket Closed: Code={code}, Reason={reason}")
        if "403" in str(reason) or "Forbidden" in str(reason):
            result["error"] = "403 Forbidden - Token invalid/expired"
        else:
            result["error"] = f"Closed: {reason}"
        test_complete.set()
    
    def on_error(ws, code, reason):
        print(f"❌ WebSocket Error: Code={code}, Reason={reason}")
        result["error"] = str(reason)
        test_complete.set()
    
    try:
        ticker = KiteTicker(api_key, access_token)
        ticker.on_connect = on_connect
        ticker.on_ticks = on_ticks
        ticker.on_close = on_close
        ticker.on_error = on_error
        
        print("   Connecting to WebSocket...")
        
        # Start in thread
        ws_thread = threading.Thread(target=ticker.connect, kwargs={"threaded": True})
        ws_thread.daemon = True
        ws_thread.start()
        
        # Wait for result (max 15 seconds)
        test_complete.wait(timeout=15)
        
        # Close connection
        try:
            ticker.close()
        except Exception as e:
            print(f"⚠ Error closing ticker: {e}")
        
        if result["connected"] and result["ticks_received"] > 0:
            print(f"\n✅ WebSocket Test: SUCCESS ({result['ticks_received']} ticks received)")
            return True
        elif result["error"]:
            print(f"\n❌ WebSocket Test: FAILED")
            print(f"   Error: {result['error']}")
            if "403" in str(result["error"]):
                print("\n🔧 DIAGNOSIS: Token is INVALID for WebSocket")
                print("   The API token works but WebSocket rejects it")
                print("   This usually means the token has expired")
            return False
        else:
            print(f"\n⚠️ WebSocket Test: TIMEOUT (no response in 15s)")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket Test: EXCEPTION - {e}")
        return False

def generate_new_token(api_key):
    """Interactive token generation"""
    print("\n" + "="*50)
    print("TOKEN GENERATION")
    print("="*50)
    
    kite = KiteConnect(api_key=api_key)
    login_url = kite.login_url()
    
    print(f"\n📌 Step 1: Open this URL in your browser:")
    print(f"\n   {login_url}\n")
    print("📌 Step 2: Login with your Zerodha credentials")
    print("📌 Step 3: After login, copy the 'request_token' from the URL")
    print("           (The page will show 'site can't be reached' - that's OK!)")
    print("           Look for: ...?request_token=XXXXXX&...")
    
    request_token = input("\n🔑 Paste the request_token here: ").strip()
    
    if not request_token:
        print("❌ No request token provided")
        return None
    
    api_secret = input("🔐 Enter your API Secret: ").strip()
    
    if not api_secret:
        print("❌ No API secret provided")
        return None
    
    try:
        data = kite.generate_session(request_token, api_secret=api_secret)
        new_token = data["access_token"]
        print(f"\n✅ New Access Token Generated!")
        print(f"   Token: {new_token[:20]}...")
        return new_token
    except Exception as e:
        print(f"\n❌ Token generation failed: {e}")
        if "used" in str(e).lower() or "expired" in str(e).lower():
            print("   The request_token was already used or expired")
            print("   → Login again to get a fresh request_token")
        return None

def update_settings(new_token):
    """Update settings file with new token"""
    try:
        with open("backend_settings.yaml", "r") as f:
            settings = yaml.safe_load(f)
        
        settings["zerodha_access_token"] = new_token
        
        with open("backend_settings.yaml", "w") as f:
            yaml.safe_dump(settings, f, sort_keys=False)
        
        print(f"✅ Updated backend_settings.yaml with new token")
        return True
    except Exception as e:
        print(f"❌ Failed to update settings: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("   ZERODHA CONNECTION DIAGNOSTIC TOOL")
    print("   " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)
    
    # Load settings
    settings = load_settings()
    if not settings:
        return
    
    api_key = settings.get("zerodha_api_key")
    access_token = settings.get("zerodha_access_token")
    
    print(f"\n📋 Configuration:")
    print(f"   API Key: {api_key}")
    print(f"   Access Token: {access_token[:20]}..." if access_token else "   Access Token: MISSING")
    
    if not api_key or not access_token:
        print("\n❌ Missing credentials in backend_settings.yaml")
        return
    
    # Test 1: API Connection
    api_ok, kite = test_api_connection(api_key, access_token)
    
    if not api_ok:
        print("\n" + "-"*50)
        choice = input("\n🔄 Generate new access token? (y/n): ").strip().lower()
        if choice == 'y':
            new_token = generate_new_token(api_key)
            if new_token:
                update_settings(new_token)
                access_token = new_token
                # Re-test
                api_ok, kite = test_api_connection(api_key, access_token)
    
    if not api_ok:
        print("\n❌ Cannot proceed without valid API connection")
        return
    
    # Test 2: WebSocket Connection
    ws_ok = test_websocket_connection(api_key, access_token)
    
    if not ws_ok:
        print("\n" + "-"*50)
        print("🔧 WebSocket failed but API works")
        print("   This is unusual - trying to regenerate token...")
        
        choice = input("\n🔄 Generate new access token? (y/n): ").strip().lower()
        if choice == 'y':
            new_token = generate_new_token(api_key)
            if new_token:
                update_settings(new_token)
                # Re-test WebSocket
                print("\n🔄 Re-testing WebSocket with new token...")
                ws_ok = test_websocket_connection(api_key, new_token)
    
    # Final Summary
    print("\n" + "="*60)
    print("   SUMMARY")
    print("="*60)
    print(f"   API Connection:       {'✅ OK' if api_ok else '❌ FAILED'}")
    print(f"   WebSocket Connection: {'✅ OK' if ws_ok else '❌ FAILED'}")
    
    if api_ok and ws_ok:
        print("\n🎉 All connections working! Restart your backend now.")
    else:
        print("\n⚠️ Issues detected. Follow the diagnostic steps above.")

if __name__ == "__main__":
    main()
