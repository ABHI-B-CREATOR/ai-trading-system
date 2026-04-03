# Telegram Alerts Setup Guide

## 📱 Get All Trading Signals on Telegram!

Your AI Trading System can send real-time alerts to your Telegram channel/group.

---

## 🚀 Quick Setup (5 Minutes)

### Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name: `AI Trading Alerts`
4. Choose a username: `your_trading_bot` (must end with `bot`)
5. **Copy the Bot Token** (looks like: `1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ`)

### Step 2: Get Your Chat ID

**Option A: For Personal Alerts (Private Chat)**
1. Start a chat with your new bot
2. Send any message to the bot
3. Open this URL in browser:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
4. Find `"chat":{"id":123456789}` - that's your Chat ID

**Option B: For Channel Alerts**
1. Create a Telegram Channel
2. Add your bot as **Administrator**
3. Post a message in the channel
4. Open the getUpdates URL (above)
5. Find the channel ID (usually starts with `-100`)

**Option C: For Group Alerts**
1. Create a Telegram Group
2. Add your bot to the group
3. Send a message mentioning the bot
4. Open the getUpdates URL
5. Find the group ID (negative number)

### Step 3: Configure Your System

Edit `8_BACKEND_APPLICATION_LAYER/backend_settings.yaml`:

```yaml
telegram:
  enabled: true
  bot_token: "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ"  # Your bot token
  chat_id: "-1001234567890"  # Your channel/group/chat ID
  
  # What to send
  send_signals: true         # Trading signals (BUY/SELL)
  send_executions: true      # Order executions
  send_risk_alerts: true     # Risk warnings
  send_ip_alerts: true       # IP change alerts
  send_daily_summary: true   # End-of-day summary
  min_confidence: 60         # Only signals with confidence >= 60%
```

### Step 4: Restart Backend

```powershell
cd c:\Users\belle\Downloads\ALGO_A1\AI_OPTIONS_TRADING_SYSTEM
python 8_BACKEND_APPLICATION_LAYER\app_server.py
```

You should see:
```
✅ Telegram Bot Connected: @your_trading_bot
✅ Telegram Alerts: Connected and Active
```

---

## 📨 What Alerts You'll Receive

### 🟢 BUY Signal
```
🟢 SIGNAL: BUY BANKNIFTY

📊 Strategy: TrendStrategy
🎯 Confidence: 75%

💰 Entry: ₹52,450.00
🎯 Target: ₹52,650.00 (+0.4%)
🛑 Stoploss: ₹52,350.00 (-0.2%)

⏰ 10:15:30
```

### 🟢🟢🟢 Strong BUY (High Confidence)
```
🟢🟢🟢 AI SIGNAL: STRONG BUY BANKNIFTY 🟢🟢🟢

🎯 Confidence: 85%
📊 Accuracy: 72%

💰 Entry: ₹52,450.00
🎯 Target: ₹52,650.00
🛑 Stoploss: ₹52,350.00

📈 Greeks: Δ=0.55 IV=18.5%

📋 Strategies: Trend, Breakout, VolExpansion

⏰ 30-Mar 10:15:30
━━━━━━━━━━━━━━━━━━━━━━
```

### ✅ Order Executed
```
✅ ORDER EXECUTED

📊 BUY BANKNIFTY
📦 Qty: 1
💰 Price: ₹52,450.00
🎯 Strategy: TrendStrategy
🔖 Order: SIM-12345678

⏰ 10:16:00
```

### 🚨 IP Change Alert
```
🚨🚨🚨 IP ADDRESS CHANGED! 🚨🚨🚨

❌ Old IP: 122.160.16.5
✅ New IP: 122.160.20.10

⚠️ ACTION REQUIRED:
1. Go to https://kite.trade/
2. Update IP Whitelist with new IP
3. Orders are BLOCKED until updated!

⏰ 30-Mar-2026 10:30:45
```

### 📈 Daily Summary
```
📈 DAILY TRADING SUMMARY

📊 Total Trades: 8
✅ Winners: 6
📈 Win Rate: 75.0%

🟢 P&L: ₹12,500.00

📅 30 March 2026
━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🔧 API Endpoints

### Check Telegram Status
```
GET http://localhost:8000/api/telegram/status
```

### Send Test Message
```
POST http://localhost:8000/api/telegram/test
```

---

## ⚠️ Troubleshooting

### Bot not responding?
1. Make sure you started a conversation with the bot
2. Check bot token is correct
3. Verify chat_id is correct (use getUpdates URL)

### Messages not appearing in channel?
1. Bot must be **Admin** in channel
2. Use channel ID starting with `-100`

### Rate limited?
- Telegram allows ~30 messages/second
- System automatically rate-limits to prevent issues

---

## 🔒 Security Tips

1. **Never share your bot token** - anyone with it can send messages
2. **Use private channel** for sensitive trade alerts
3. **Don't add strangers** to your alert channel/group

---

## 📞 Need Help?

- **Telegram Bot API**: https://core.telegram.org/bots/api
- **BotFather**: @BotFather on Telegram

---

*Last Updated: March 30, 2026*
