# 🟦 Zerodha Integration Guide

## ⚡ Quick Note

**Your system is already running in DEMO MODE** with simulated market data. You only need Zerodha credentials if you want **real live market data**.

If demo mode is working fine for you, **skip all these steps!**

---

## Step 1: Create Zerodha Account (Optional)
- Go to: https://kite.zerodha.com
- Sign up with email/mobile
- Complete KYC verification (usually 5-10 mins)

## Step 2: Get API Credentials

**Method 1: Direct API Link (Fastest)**
```
https://console.zerodha.com/settings/api
```
Just visit that URL directly! You should see "API Tokens" section.

**Method 2: Via Console Navigation**
1. Go to: https://console.zerodha.com
2. In top-right corner, click your **profile/account icon**
3. Select **Settings** → **API Tokens** (or look for Developer section)
4. Click **"Create new token"** or **"Generate"**
5. Copy:
   - **API Key** (like: `abc123def456`)
   - **API Secret** (like: `xyz789uvw123`) - **Save this, it won't show again!**

**Method 3: If not found in Settings**
1. In console, look for **gear icon** (⚙️) in navigation
2. Find **"Developers"** or **"API"** section
3. Click **"New API Token"**
4. Copy both values

## Step 3: Get Access Token

### **Quick Method (Recommended)**

Run this command to get your access token:

```powershell
python << 'EOF'
from kiteconnect import KiteConnect

# Use placeholder - you'll enter real credentials interactively
api_key = input("Enter your Zerodha API Key: ")

kite = KiteConnect(api_key=api_key)
print("\n🔗 Open this URL in your browser and login:\n")
print(kite.login_url())

request_token = input("\nAfter login, copy the REQUEST_TOKEN from URL and paste here: ")
api_secret = input("Enter your API Secret: ")

try:
    data = kite.generate_session(request_token, api_secret=api_secret)
    print(f"\n✅ Access Token: {data['access_token']}")
    print(f"📌 Copy this token to your config!")
except Exception as e:
    print(f"❌ Error: {e}")
EOF
```

### **One-Click Helper Script (Auto-writes `backend_settings.yaml`)**

If you want a faster flow, run:

```powershell
python 8_BACKEND_APPLICATION_LAYER/zerodha_token_helper.py
```

This will:
1. Ask for your API key + secret
2. Show the login URL
3. Accept the `request_token`
4. Generate the access token and write it to `8_BACKEND_APPLICATION_LAYER/backend_settings.yaml`

### **Auto-Capture Callback (No ngrok error page)**

To avoid the ngrok error page, set your Zerodha app Redirect URL to:

```
http://127.0.0.1:5000
```

Then run:

```powershell
python 8_BACKEND_APPLICATION_LAYER/zerodha_token_helper.py --auto
```

This starts a tiny local callback listener, opens the login URL, and captures the `request_token` automatically.

### **Manual Method**

If the script doesn't work:

1. Get your **API Key** and **API Secret** from Zerodha console
2. Run:
```powershell
python -c "
from kiteconnect import KiteConnect
kite = KiteConnect(api_key='YOUR_API_KEY')
print('Login here:', kite.login_url())
"
```
3. Visit the URL, login to Zerodha
4. Copy the `request_token` from redirect URL
5. Run:
```powershell
python -c "
from kiteconnect import KiteConnect
kite = KiteConnect(api_key='YOUR_API_KEY')
data = kite.generate_session('REQUEST_TOKEN_HERE', api_secret='YOUR_API_SECRET')
print('Access Token:', data['access_token'])
"
```

## Step 4: Update Your Config

Edit: `8_BACKEND_APPLICATION_LAYER/backend_settings.yaml` (or update app_server.py defaults)

```yaml
broker: zerodha
zerodha_api_key: "your_api_key_from_console"
zerodha_access_token: "your_access_token_generated"
symbols:
  - BANKNIFTY
  - NIFTY
  - FINNIFTY
trading_mode: paper
demo_mode: false
```

## Step 5: Restart Backend

```powershell
cd c:\Users\belle\Downloads\ALGO_A1\AI_OPTIONS_TRADING_SYSTEM
python -u "8_BACKEND_APPLICATION_LAYER/app_server.py"
```

## ✅ Success!

Look for:
```
🟦 Using Zerodha KiteConnect
📡 Market Data Feed Started
```

---

## 🔄 If Zerodha Auth Fails: Demo Mode

The system automatically falls back to **demo mode** if:
- Access token is invalid
- Zerodha credenti are not set

Demo mode generates simulated market data, so your dashboard still works!

---

## 📞 Support

- Zerodha Docs: https://kite.trade/docs/quick-start
- API Issues: support@zerodha.com

Running the start_ai.ps1
cd "C:\Users\tripa\Downloads\ALGO_A1 (2)\AI_OPTIONS_TRADING_SYSTEM"
powershell -ExecutionPolicy Bypass -File .\start_ai.ps1
