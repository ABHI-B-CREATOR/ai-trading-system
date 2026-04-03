# 🚀 Railway Cloud Deployment Guide

## Step 1: Create Railway Account
1. Go to https://railway.app
2. Sign up with GitHub (recommended) or email

## Step 2: Install Railway CLI (Optional but recommended)
```bash
npm install -g @railway/cli
railway login
```

## Step 3: Deploy via GitHub (Easiest)

### Option A: Using GitHub (Recommended)
1. Push your code to GitHub:
   ```bash
   cd c:\Users\tripa\Downloads\ALGO_A1\AI_OPTIONS_TRADING_SYSTEM
   git init
   git add .
   git commit -m "Initial commit for Railway deployment"
   git remote add origin https://github.com/YOUR_USERNAME/ai-trading-system.git
   git push -u origin main
   ```

2. On Railway Dashboard:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will auto-detect Python and deploy

### Option B: Using Railway CLI
```bash
cd c:\Users\tripa\Downloads\ALGO_A1\AI_OPTIONS_TRADING_SYSTEM
railway init
railway up
```

## Step 4: Set Environment Variables

In Railway Dashboard → Your Project → Variables:

```
ZERODHA_API_KEY=your_api_key
ZERODHA_API_SECRET=your_api_secret
ZERODHA_ACCESS_TOKEN=your_access_token
FYERS_APP_ID=your_fyers_app_id
FYERS_SECRET=your_fyers_secret
FLASK_ENV=production
PORT=5000
```

## Step 5: Get Your API URL

After deployment, Railway gives you a URL like:
```
https://ai-trading-system-production.up.railway.app
```

This is your **BACKEND_API_URL** for the mobile app.

## Step 6: Configure WebSocket

Your WebSocket will be available at:
```
wss://ai-trading-system-production.up.railway.app/ws
```

---

## 📱 After Deployment

Once deployed, note these URLs for your mobile app:
- **REST API**: `https://YOUR_APP.up.railway.app/api/`
- **WebSocket**: `wss://YOUR_APP.up.railway.app:8765`

---

## ⚠️ Important Notes

1. **Zerodha Token Refresh**: You'll need to refresh your Zerodha access token daily. Consider setting up the token helper endpoint.

2. **Free Tier Limits**: Railway free tier has 500 hours/month. This is enough for market hours (6.25 hrs × 22 days = 137.5 hrs).

3. **Keep Alive**: The app won't sleep if you have `sleepApplication: false` in railway.json.

---

## 🔧 Troubleshooting

View logs:
```bash
railway logs
```

Restart deployment:
```bash
railway up --detach
```
