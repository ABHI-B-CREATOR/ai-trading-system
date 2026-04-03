"""
Telegram Alert Service
======================
Sends trading signals, alerts, and notifications to Telegram channel/chat.
"""

import requests
import threading
import queue
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger("TELEGRAM_ALERTS")


class TelegramAlertService:
    """
    Sends real-time trading alerts to Telegram.
    """
    
    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        """
        Initialize Telegram alert service.
        
        Args:
            bot_token: Telegram Bot API token (from @BotFather)
            chat_id: Channel/Group/Chat ID to send messages to
            enabled: Enable/disable sending
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Message queue for async sending
        self.message_queue = queue.Queue()
        self.running = True
        
        # Rate limiting (Telegram allows ~30 msg/sec)
        self.last_send_time = 0
        self.min_interval = 0.05  # 50ms between messages
        
        # Start background sender thread
        self._start_sender_thread()
        
        if enabled:
            print(f"📱 Telegram Alerts Enabled (Chat: {chat_id})")
        else:
            print("📱 Telegram Alerts Disabled")
    
    def _start_sender_thread(self):
        """Start background thread for sending messages."""
        def sender():
            while self.running:
                try:
                    # Get message from queue (timeout to allow shutdown)
                    try:
                        message = self.message_queue.get(timeout=1)
                    except queue.Empty:
                        continue
                    
                    # Rate limiting
                    elapsed = time.time() - self.last_send_time
                    if elapsed < self.min_interval:
                        time.sleep(self.min_interval - elapsed)
                    
                    # Send message
                    self._send_message_sync(message)
                    self.last_send_time = time.time()
                    
                except Exception as e:
                    logger.error(f"Telegram sender error: {e}")
        
        thread = threading.Thread(target=sender, daemon=True)
        thread.start()
    
    def _send_message_sync(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send message synchronously."""
        if not self.enabled or not self.bot_token or not self.chat_id:
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Telegram API error: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    def send(self, text: str):
        """Queue a message for sending."""
        if self.enabled:
            self.message_queue.put(text)
    
    def send_signal(self, signal: Dict[str, Any]):
        """Send a trading signal alert."""
        direction = signal.get("direction", "HOLD")
        symbol = signal.get("symbol", "UNKNOWN")
        strategy = signal.get("strategy", "unknown")
        confidence = signal.get("confidence", 0)
        entry = signal.get("entry_price", 0)
        target = signal.get("target", 0)
        stoploss = signal.get("stoploss", 0)
        
        # Emoji based on direction
        if direction == "BUY":
            emoji = "🟢"
            action = "BUY"
        elif direction == "SELL":
            emoji = "🔴"
            action = "SELL"
        else:
            emoji = "⚪"
            action = "HOLD"
        
        # Calculate potential P&L
        if direction == "BUY" and entry and target:
            potential = ((target - entry) / entry) * 100
            risk = ((entry - stoploss) / entry) * 100 if stoploss else 0
        elif direction == "SELL" and entry and target:
            potential = ((entry - target) / entry) * 100
            risk = ((stoploss - entry) / entry) * 100 if stoploss else 0
        else:
            potential = 0
            risk = 0
        
        message = f"""
{emoji} <b>SIGNAL: {action} {symbol}</b>

📊 <b>Strategy:</b> {strategy}
🎯 <b>Confidence:</b> {confidence:.0f}%

💰 <b>Entry:</b> ₹{entry:,.2f}
🎯 <b>Target:</b> ₹{target:,.2f} (+{potential:.1f}%)
🛑 <b>Stoploss:</b> ₹{stoploss:,.2f} (-{risk:.1f}%)

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        self.send(message.strip())
    
    def send_unified_signal(self, unified: Dict[str, Any]):
        """Send unified signal from all strategies."""
        direction = unified.get("direction", "HOLD")
        symbol = unified.get("symbol", "UNKNOWN")
        confidence = unified.get("confidence", 0)
        accuracy = unified.get("accuracy", 0)
        entry = unified.get("entry_price", 0)
        target = unified.get("target", 0)
        stoploss = unified.get("stoploss", 0)
        strategies = unified.get("contributing_strategies", [])
        greeks = unified.get("greeks", {})
        
        # Strong signal threshold
        is_strong = confidence >= 70
        
        if direction == "BUY":
            emoji = "🟢🟢🟢" if is_strong else "🟢"
            header = "STRONG BUY" if is_strong else "BUY"
        elif direction == "SELL":
            emoji = "🔴🔴🔴" if is_strong else "🔴"
            header = "STRONG SELL" if is_strong else "SELL"
        else:
            return  # Don't send HOLD signals
        
        # Greeks info
        greeks_text = ""
        if greeks:
            delta = greeks.get("delta", 0)
            iv = greeks.get("iv", 0)
            greeks_text = f"\n📈 <b>Greeks:</b> Δ={delta:.3f} IV={iv:.1f}%"
        
        message = f"""
{emoji} <b>AI SIGNAL: {header} {symbol}</b> {emoji}

🎯 <b>Confidence:</b> {confidence:.0f}%
📊 <b>Accuracy:</b> {accuracy:.0f}%

💰 <b>Entry:</b> ₹{entry:,.2f}
🎯 <b>Target:</b> ₹{target:,.2f}
🛑 <b>Stoploss:</b> ₹{stoploss:,.2f}
{greeks_text}

📋 <b>Strategies:</b> {', '.join(strategies)}

⏰ {datetime.now().strftime('%d-%b %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━
"""
        self.send(message.strip())
    
    def send_trade_execution(self, trade: Dict[str, Any]):
        """Send trade execution notification."""
        symbol = trade.get("symbol", "UNKNOWN")
        side = trade.get("side", "BUY")
        qty = trade.get("qty", 1)
        price = trade.get("entry_price", 0)
        order_id = trade.get("order_id", "")
        strategy = trade.get("strategy", "")
        
        emoji = "✅" if side == "BUY" else "🔻"
        
        message = f"""
{emoji} <b>ORDER EXECUTED</b>

📊 {side} {symbol}
📦 Qty: {qty}
💰 Price: ₹{price:,.2f}
🎯 Strategy: {strategy}
🔖 Order: {order_id}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        self.send(message.strip())
    
    def send_risk_alert(self, level: str, title: str, message: str):
        """Send risk/system alert."""
        if level.lower() == "critical":
            emoji = "🚨🚨🚨"
        elif level.lower() == "warning":
            emoji = "⚠️"
        else:
            emoji = "ℹ️"
        
        alert = f"""
{emoji} <b>{level.upper()}: {title}</b>

{message}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        self.send(alert.strip())
    
    def send_ip_change_alert(self, old_ip: str, new_ip: str):
        """Send IP change alert."""
        message = f"""
🚨🚨🚨 <b>IP ADDRESS CHANGED!</b> 🚨🚨🚨

❌ Old IP: <code>{old_ip}</code>
✅ New IP: <code>{new_ip}</code>

⚠️ <b>ACTION REQUIRED:</b>
1. Go to https://kite.trade/
2. Update IP Whitelist with new IP
3. Orders are BLOCKED until updated!

⏰ {datetime.now().strftime('%d-%b %H:%M:%S')}
"""
        self.send(message.strip())
    
    def send_daily_summary(self, summary: Dict[str, Any]):
        """Send end-of-day summary."""
        total_trades = summary.get("total_trades", 0)
        winning = summary.get("winning_trades", 0)
        pnl = summary.get("pnl", 0)
        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
        
        emoji = "📈" if pnl >= 0 else "📉"
        pnl_emoji = "🟢" if pnl >= 0 else "🔴"
        
        message = f"""
{emoji} <b>DAILY TRADING SUMMARY</b>

📊 Total Trades: {total_trades}
✅ Winners: {winning}
📈 Win Rate: {win_rate:.1f}%

{pnl_emoji} <b>P&L: ₹{pnl:,.2f}</b>

📅 {datetime.now().strftime('%d %B %Y')}
━━━━━━━━━━━━━━━━━━━━━━
"""
        self.send(message.strip())
    
    def send_market_open(self):
        """Send market open notification."""
        message = f"""
🔔 <b>MARKET OPEN</b>

📈 NSE/BSE trading session started
🤖 AI Trading System: ACTIVE
📊 Monitoring: BANKNIFTY, NIFTY, FINNIFTY

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        self.send(message.strip())
    
    def send_market_close(self):
        """Send market close notification."""
        message = f"""
🔔 <b>MARKET CLOSED</b>

📊 Trading session ended
🤖 AI System: Switching to analysis mode

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        self.send(message.strip())
    
    def test_connection(self) -> bool:
        """Test Telegram connection."""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                bot_info = response.json().get("result", {})
                bot_name = bot_info.get("username", "Unknown")
                print(f"✅ Telegram Bot Connected: @{bot_name}")
                
                # Send test message
                test_msg = f"""
🤖 <b>AI Trading System Connected!</b>

✅ Telegram alerts are now active
📊 You will receive:
• Trading signals (BUY/SELL)
• Order executions
• Risk alerts
• IP change warnings
• Daily summaries

⏰ {datetime.now().strftime('%d-%b-%Y %H:%M:%S')}
"""
                return self._send_message_sync(test_msg.strip())
            return False
        except Exception as e:
            print(f"❌ Telegram connection failed: {e}")
            return False
    
    def stop(self):
        """Stop the sender thread."""
        self.running = False


# Singleton instance
_telegram_instance: Optional[TelegramAlertService] = None


def get_telegram_service(config: dict = None) -> Optional[TelegramAlertService]:
    """Get or create Telegram service singleton."""
    global _telegram_instance
    
    if _telegram_instance is None and config:
        telegram_config = config.get("telegram", {})
        bot_token = telegram_config.get("bot_token", "")
        chat_id = telegram_config.get("chat_id", "")
        enabled = telegram_config.get("enabled", False)
        
        if bot_token and chat_id:
            _telegram_instance = TelegramAlertService(
                bot_token=bot_token,
                chat_id=chat_id,
                enabled=enabled
            )
    
    return _telegram_instance


def init_telegram(bot_token: str, chat_id: str, enabled: bool = True) -> TelegramAlertService:
    """Initialize Telegram service with credentials."""
    global _telegram_instance
    _telegram_instance = TelegramAlertService(
        bot_token=bot_token,
        chat_id=chat_id,
        enabled=enabled
    )
    return _telegram_instance
