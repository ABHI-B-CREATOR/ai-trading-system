# SEBI Static IP Compliance Guide

## ⚠️ URGENT: SEBI Regulation (Effective April 1, 2026)

Per SEBI regulations, all API-based trading orders must originate from a **registered static IP address**. Orders from unregistered IPs will be **rejected**.

---

## 📋 Step 1: Register Your IP on Kite Connect (DO THIS NOW!)

1. **Go to**: https://kite.trade/
2. **Login** with your Zerodha credentials
3. **Click on "Profile"** in the top menu
4. **Find "IP Whitelist"** section (you can add up to 2 IPs)
5. **Enter your IP**: 
   ```
   122.160.16.5
   ```
6. **Check** the confirmation box: "I confirm that the above static IPs will be used exclusively by me and/or my immediate family"
7. **Save** the changes

---

## ⚠️ IMPORTANT: You Have a DYNAMIC IP!

Your ISP: **Bharti Airtel** (Consumer Broadband)
Your IP Type: **DYNAMIC** (may change!)

### When Does IP Change?
- Router restart
- Power outage  
- ISP maintenance
- Sometimes after 24-48 hours

---

## 🔄 Step 2: Options for Dynamic IP Users

### Option A: Get Static IP from Airtel (RECOMMENDED)
- **Call**: 121 (Airtel Customer Care)
- **Request**: "Static IP add-on for broadband"
- **Cost**: ₹500-1500/month extra
- **Benefit**: IP never changes, no more updates needed

### Option B: Cloud Server Deployment
- Deploy on AWS/GCP/Azure/DigitalOcean
- Get a fixed Elastic IP
- Run trading system from cloud
- Cost: ~₹1000-3000/month

### Option C: VPN with Static IP
- Use VPN with dedicated static IP
- Register VPN's IP with Zerodha
- Always connect via VPN before trading

---

## 🛡️ Auto-Protection Built Into Your System

Your trading system now has SEBI IP compliance protection:

### ✅ What It Does:
1. **Monitors IP** every 5 minutes
2. **Alerts you** with loud notification if IP changes
3. **Blocks orders** automatically if IP doesn't match
4. **Prevents SEBI rejection** by catching issues locally

### API Endpoints:
```
GET http://localhost:8000/api/ip-status    - Check current status
GET http://localhost:8000/api/ip-validate  - Validate trading allowed
POST http://localhost:8000/api/ip-add/X.X.X.X - Add new IP
```

---

## 🚨 What To Do When IP Changes

You'll see this alert:
```
╔══════════════════════════════════════════════════════════════╗
║  🚨 IP ADDRESS CHANGED - ACTION REQUIRED!                    ║
╠══════════════════════════════════════════════════════════════╣
║  Old IP: 122.160.16.5                                        ║
║  New IP: X.X.X.X                                             ║
╠══════════════════════════════════════════════════════════════╣
║  ⚠️  UPDATE REQUIRED ON KITE CONNECT                         ║
╚══════════════════════════════════════════════════════════════╝
```

**Steps:**
1. Note your new IP from the alert
2. Go to https://kite.trade/ → Profile → IP Whitelist
3. Update with new IP
4. Update `backend_settings.yaml`:
   ```yaml
   registered_ips:
     - "NEW_IP_HERE"
   ```
5. Restart backend

---

## ⚙️ Current Configuration

File: `backend_settings.yaml`

```yaml
# SEBI Compliance Settings
sebi_compliance:
  static_ip_check: true
  registered_ips:
    - "122.160.16.5"  # Your current IP - UPDATE WHEN CHANGED
  ip_check_interval_seconds: 300
  block_orders_on_ip_mismatch: true
```

---

## 🔐 IP History Log

All IP changes are logged to: `logs/ip_changes.log`

---

## 📞 Support Contacts

- **Airtel Static IP**: Call 121
- **Zerodha Support**: support@zerodha.com
- **Kite Connect API**: https://kite.trade/forum
- **SEBI Helpline**: 1800-22-7575

---

*Last Updated: March 30, 2026*
*Current IP: 122.160.16.5 (Airtel Delhi - Dynamic)*
