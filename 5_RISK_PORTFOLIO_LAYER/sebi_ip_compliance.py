"""
SEBI Static IP Compliance Module
================================
Validates that trading requests originate from registered static IPs
as per SEBI regulations effective April 1, 2026.
"""

import os
import requests
import threading
import time
import logging
from datetime import datetime
from typing import List, Optional, Dict

logger = logging.getLogger("SEBI_COMPLIANCE")


class SEBIIPCompliance:
    """
    Ensures trading system complies with SEBI static IP requirements.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        
        # Load registered IPs from config
        sebi_config = self.config.get("sebi_compliance", {})
        self.registered_ips: List[str] = sebi_config.get("registered_ips", [])
        self.ip_check_enabled: bool = sebi_config.get("static_ip_check", True)
        self.check_interval: int = sebi_config.get("ip_check_interval_seconds", 300)
        self.block_on_mismatch: bool = sebi_config.get("block_orders_on_ip_mismatch", True)
        
        # State
        self.current_ip: Optional[str] = None
        self.last_check_time: Optional[datetime] = None
        self.ip_match: bool = False
        self.can_trade: bool = True
        self.ip_history: List[Dict] = []
        
        # Callbacks
        self.on_ip_change_callback = None
        self.on_ip_mismatch_callback = None
        
        # Start background IP monitor
        self._start_ip_monitor()
        
        print("🔐 SEBI IP Compliance Module Initialized")
    
    def _get_public_ip(self) -> Optional[str]:
        """Fetch current public IP address."""
        ip_services = [
            "https://api.ipify.org?format=json",
            "https://ipinfo.io/json",
            "https://api.myip.com"
        ]
        
        for service in ip_services:
            try:
                response = requests.get(service, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("ip") or data.get("ip")
            except Exception:
                continue
        
        return None
    
    def _start_ip_monitor(self):
        """Start background thread to monitor IP changes."""
        def monitor():
            while True:
                try:
                    new_ip = self._get_public_ip()
                    
                    if new_ip:
                        old_ip = self.current_ip
                        self.current_ip = new_ip
                        self.last_check_time = datetime.now()
                        
                        # Check if IP matches registered IPs
                        self.ip_match = new_ip in self.registered_ips
                        self.can_trade = self.ip_match or not self.block_on_mismatch
                        
                        # Detect IP change
                        if old_ip and old_ip != new_ip:
                            self._on_ip_change(old_ip, new_ip)
                        
                        # Alert on mismatch
                        if not self.ip_match and self.registered_ips:
                            self._on_ip_mismatch(new_ip)
                        
                        # Log status
                        status = "✅ MATCH" if self.ip_match else "⚠️ MISMATCH"
                        logger.info(f"IP Check: {new_ip} {status}")
                        
                except Exception as e:
                    logger.error(f"IP monitor error: {e}")
                
                time.sleep(self.check_interval)
        
        if self.ip_check_enabled:
            thread = threading.Thread(target=monitor, daemon=True)
            thread.start()
            print(f"📡 IP Monitor Started (checking every {self.check_interval}s)")
    
    def _on_ip_change(self, old_ip: str, new_ip: str):
        """Handle IP address change."""
        self.ip_history.append({
            "old_ip": old_ip,
            "new_ip": new_ip,
            "timestamp": datetime.now().isoformat()
        })
        
        # Create detailed alert message
        alert_msg = f"""
╔══════════════════════════════════════════════════════════════╗
║  🚨 IP ADDRESS CHANGED - ACTION REQUIRED!                    ║
╠══════════════════════════════════════════════════════════════╣
║  Old IP: {old_ip:<50} ║
║  New IP: {new_ip:<50} ║
║  Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S'):<50} ║
╠══════════════════════════════════════════════════════════════╣
║  ⚠️  UPDATE REQUIRED ON KITE CONNECT:                        ║
║                                                              ║
║  1. Go to: https://kite.trade/                               ║
║  2. Login → Profile → API IP Whitelist                       ║
║  3. Replace old IP with: {new_ip:<34} ║
║  4. Save changes                                             ║
║                                                              ║
║  ⛔ Orders will be BLOCKED until IP is updated!              ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(alert_msg)
        
        # Log to file for record
        self._log_ip_change(old_ip, new_ip)
        
        if self.on_ip_change_callback:
            try:
                self.on_ip_change_callback(old_ip, new_ip)
            except Exception:
                pass
    
    def _on_ip_mismatch(self, current_ip: str):
        """Handle IP mismatch with registered IPs."""
        alert_msg = f"""
╔══════════════════════════════════════════════════════════════╗
║  🚫 SEBI IP COMPLIANCE VIOLATION                             ║
╠══════════════════════════════════════════════════════════════╣
║  Current IP:    {current_ip:<44} ║
║  Registered:    {', '.join(self.registered_ips):<44} ║
╠══════════════════════════════════════════════════════════════╣
║  ⛔ ALL ORDERS BLOCKED until IP is registered!               ║
║                                                              ║
║  Fix: Update IP Whitelist on https://kite.trade/            ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(alert_msg)
        
        if self.on_ip_mismatch_callback:
            try:
                self.on_ip_mismatch_callback(current_ip, self.registered_ips)
            except Exception:
                pass
    
    def _log_ip_change(self, old_ip: str, new_ip: str):
        """Log IP changes to file for tracking."""
        try:
            log_file = "logs/ip_changes.log"
            os.makedirs("logs", exist_ok=True)
            with open(log_file, "a") as f:
                f.write(f"{datetime.now().isoformat()} | {old_ip} -> {new_ip}\n")
        except Exception:
            pass
    
    def validate_order_ip(self) -> Dict:
        """
        Validate if current IP is allowed to place orders.
        Call this before placing any order.
        
        Returns:
            Dict with validation status
        """
        if not self.ip_check_enabled:
            return {
                "allowed": True,
                "reason": "IP check disabled",
                "current_ip": self.current_ip
            }
        
        if not self.registered_ips:
            return {
                "allowed": True,
                "reason": "No registered IPs configured",
                "current_ip": self.current_ip,
                "warning": "Configure registered_ips for SEBI compliance"
            }
        
        if self.ip_match:
            return {
                "allowed": True,
                "reason": "IP matches registered IP",
                "current_ip": self.current_ip,
                "registered_ips": self.registered_ips
            }
        
        if self.block_on_mismatch:
            return {
                "allowed": False,
                "reason": f"IP {self.current_ip} not in registered IPs. Order blocked per SEBI compliance.",
                "current_ip": self.current_ip,
                "registered_ips": self.registered_ips,
                "action_required": "Register current IP in Kite Connect profile or connect from registered network"
            }
        
        return {
            "allowed": True,
            "reason": "IP mismatch but blocking disabled",
            "current_ip": self.current_ip,
            "warning": "Order may be rejected by Zerodha due to SEBI IP restrictions"
        }
    
    def add_registered_ip(self, ip: str):
        """Add a new IP to registered IPs list."""
        if ip not in self.registered_ips:
            self.registered_ips.append(ip)
            self.ip_match = self.current_ip in self.registered_ips
            print(f"✅ Added registered IP: {ip}")
    
    def remove_registered_ip(self, ip: str):
        """Remove an IP from registered IPs list."""
        if ip in self.registered_ips:
            self.registered_ips.remove(ip)
            self.ip_match = self.current_ip in self.registered_ips
            print(f"❌ Removed registered IP: {ip}")
    
    def get_status(self) -> Dict:
        """Get current IP compliance status."""
        return {
            "current_ip": self.current_ip,
            "registered_ips": self.registered_ips,
            "ip_match": self.ip_match,
            "can_trade": self.can_trade,
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "ip_check_enabled": self.ip_check_enabled,
            "block_on_mismatch": self.block_on_mismatch,
            "ip_history": self.ip_history[-10:]  # Last 10 changes
        }
    
    def set_callbacks(self, on_ip_change=None, on_ip_mismatch=None):
        """Set callback functions for IP events."""
        if on_ip_change:
            self.on_ip_change_callback = on_ip_change
        if on_ip_mismatch:
            self.on_ip_mismatch_callback = on_ip_mismatch


# Singleton instance
_compliance_instance = None

def get_ip_compliance(config: dict = None) -> SEBIIPCompliance:
    """Get or create the global IP compliance checker."""
    global _compliance_instance
    if _compliance_instance is None:
        _compliance_instance = SEBIIPCompliance(config)
    return _compliance_instance
