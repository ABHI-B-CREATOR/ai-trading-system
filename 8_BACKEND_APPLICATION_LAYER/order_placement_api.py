"""
Order Placement API - Manual Buy/Sell Execution
Provides REST endpoints for placing, modifying, and tracking orders.
Supports both Paper Trading and Live Trading modes.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import os
import sys
import uuid

# Add parent directories for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '6_EXECUTION_LAYER'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '5_RISK_PORTFOLIO_LAYER'))

try:
    from sebi_ip_compliance import get_ip_compliance  # type: ignore
except ImportError:
    get_ip_compliance = None


class OrderPlacementAPI:
    """
    REST API for manual order placement from the dashboard.
    Supports Paper Trading (simulated) and Live Trading (Zerodha/Kite).
    """

    def __init__(self, order_router, trade_logger, market_feed=None, 
                 notification_service=None, risk_engine=None):
        """
        Args:
            order_router: OrderRouter instance for execution
            trade_logger: TradeLogger for recording trades
            market_feed: ZerodhaSocketFeed for live prices and positions
            notification_service: NotificationService for alerts
            risk_engine: RiskRuntimeEngine for validation
        """
        self.order_router = order_router
        self.trade_logger = trade_logger
        self.market_feed = market_feed
        self.notification_service = notification_service
        self.risk_engine = risk_engine
        
        # SEBI IP Compliance
        self.ip_compliance = get_ip_compliance() if get_ip_compliance else None
        
        # In-memory position tracking (paper mode)
        self.paper_positions = {}
        self.paper_orders = {}
        
        # Blueprint
        self.blueprint = Blueprint(
            "order_placement_api",
            __name__,
            url_prefix="/api/order"
        )
        
        self._register_routes()
        print("📝 Order Placement API Initialized")

    def _register_routes(self):
        """Register all order-related endpoints."""
        
        # ===== PLACE ORDER =====
        @self.blueprint.route("/place", methods=["POST"])
        def place_order():
            """
            Place a new order (Buy or Sell).
            
            Request Body:
            {
                "symbol": "BANKNIFTY24MAR52000CE",
                "exchange": "NFO",
                "side": "BUY" | "SELL",
                "qty": 15,
                "order_type": "MARKET" | "LIMIT",
                "price": 250.50,  (required for LIMIT)
                "stoploss": 220.00,  (optional)
                "target": 310.00,  (optional)
                "mode": "paper" | "live"
            }
            """
            try:
                body = request.json
                
                # Validate required fields
                required = ["symbol", "side", "qty", "order_type"]
                missing = [f for f in required if not body.get(f)]
                if missing:
                    return jsonify({
                        "status": "ERROR",
                        "message": f"Missing required fields: {', '.join(missing)}"
                    }), 400
                
                symbol = body.get("symbol")
                exchange = body.get("exchange", "NFO")
                side = body.get("side", "").upper()
                qty = int(body.get("qty", 0))
                order_type = body.get("order_type", "MARKET").upper()
                price = float(body.get("price", 0)) if body.get("price") else None
                stoploss = float(body.get("stoploss", 0)) if body.get("stoploss") else None
                target = float(body.get("target", 0)) if body.get("target") else None
                mode = body.get("mode", "paper").lower()
                
                # Validate side
                if side not in ["BUY", "SELL"]:
                    return jsonify({
                        "status": "ERROR",
                        "message": "Side must be 'BUY' or 'SELL'"
                    }), 400
                
                # Validate qty
                if qty <= 0:
                    return jsonify({
                        "status": "ERROR",
                        "message": "Quantity must be greater than 0"
                    }), 400
                
                # Validate LIMIT order has price
                if order_type == "LIMIT" and not price:
                    return jsonify({
                        "status": "ERROR",
                        "message": "Price required for LIMIT orders"
                    }), 400
                
                # Get current market price
                ltp = self._get_ltp(symbol)
                entry_price = price if order_type == "LIMIT" else ltp
                
                if not entry_price:
                    return jsonify({
                        "status": "ERROR",
                        "message": f"Could not fetch price for {symbol}"
                    }), 400
                
                # SEBI IP check for live orders
                if mode == "live":
                    ip_check = self._check_sebi_compliance()
                    if not ip_check["allowed"]:
                        return jsonify({
                            "status": "REJECTED",
                            "message": ip_check["reason"],
                            "ip_compliance": ip_check
                        }), 403
                
                # Risk validation
                if self.risk_engine and mode == "live":
                    risk_check = self.risk_engine.validate_order({
                        "symbol": symbol,
                        "side": side,
                        "qty": qty,
                        "price": entry_price
                    })
                    if not risk_check.get("allowed", True):
                        return jsonify({
                            "status": "REJECTED",
                            "message": risk_check.get("reason", "Risk check failed")
                        }), 403
                
                # Execute order
                if mode == "paper":
                    result = self._execute_paper_order(
                        symbol, exchange, side, qty, order_type, 
                        entry_price, stoploss, target
                    )
                else:
                    result = self._execute_live_order(
                        symbol, exchange, side, qty, order_type,
                        entry_price, stoploss, target
                    )
                
                # Send notification
                if self.notification_service and result.get("status") == "EXECUTED":
                    self.notification_service.notify_trade(result)
                
                return jsonify(result)
                
            except Exception as e:
                print(f"❌ Order placement error: {e}")
                return jsonify({
                    "status": "ERROR",
                    "message": str(e)
                }), 500

        # ===== GET ORDER STATUS =====
        @self.blueprint.route("/status/<order_id>", methods=["GET"])
        def get_order_status(order_id):
            """Get status of a specific order."""
            try:
                # Check paper orders
                if order_id in self.paper_orders:
                    return jsonify(self.paper_orders[order_id])
                
                # Check with broker (live orders)
                if self.market_feed and hasattr(self.market_feed, 'kite'):
                    try:
                        orders = self.market_feed.kite.orders()
                        for order in orders:
                            if order.get("order_id") == order_id:
                                return jsonify({
                                    "order_id": order_id,
                                    "status": order.get("status"),
                                    "symbol": order.get("tradingsymbol"),
                                    "side": order.get("transaction_type"),
                                    "qty": order.get("quantity"),
                                    "filled_qty": order.get("filled_quantity"),
                                    "price": order.get("price"),
                                    "avg_price": order.get("average_price")
                                })
                    except Exception as e:
                        print(f"⚠️ Kite order fetch error: {e}")
                
                return jsonify({
                    "status": "NOT_FOUND",
                    "message": f"Order {order_id} not found"
                }), 404
                
            except Exception as e:
                return jsonify({"status": "ERROR", "message": str(e)}), 500

        # ===== GET POSITIONS =====
        @self.blueprint.route("/positions", methods=["GET"])
        def get_positions():
            """Get all open positions (paper + live)."""
            try:
                mode = request.args.get("mode", "all")
                positions = []
                
                # Paper positions
                if mode in ["all", "paper"]:
                    for pos_id, pos in self.paper_positions.items():
                        # Update with current LTP
                        ltp = self._get_ltp(pos["symbol"])
                        if ltp:
                            pos["ltp"] = ltp
                            pos["pnl"] = self._calculate_pnl(pos, ltp)
                            pos["pnl_pct"] = (pos["pnl"] / (pos["avg_price"] * pos["qty"])) * 100
                        positions.append({**pos, "mode": "paper"})
                
                # Live positions from Kite
                if mode in ["all", "live"] and self.market_feed:
                    live_positions = self._get_live_positions()
                    for pos in live_positions:
                        pos["mode"] = "live"
                        positions.append(pos)
                
                return jsonify({
                    "positions": positions,
                    "count": len(positions),
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                return jsonify({"status": "ERROR", "message": str(e)}), 500

        # ===== SQUARE OFF POSITION =====
        @self.blueprint.route("/square_off", methods=["POST"])
        def square_off():
            """
            Square off (close) a position.
            
            Request Body:
            {
                "position_id": "POS-12345",
                "qty": 15,  (optional - partial exit)
                "mode": "paper" | "live"
            }
            """
            try:
                body = request.json
                position_id = body.get("position_id")
                exit_qty = body.get("qty")
                mode = body.get("mode", "paper")
                
                if not position_id:
                    return jsonify({
                        "status": "ERROR",
                        "message": "position_id required"
                    }), 400
                
                if mode == "paper":
                    result = self._square_off_paper(position_id, exit_qty)
                else:
                    result = self._square_off_live(position_id, exit_qty)
                
                return jsonify(result)
                
            except Exception as e:
                return jsonify({"status": "ERROR", "message": str(e)}), 500

        # ===== MODIFY ORDER (SL/Target) =====
        @self.blueprint.route("/modify/<order_id>", methods=["PUT"])
        def modify_order(order_id):
            """
            Modify an existing order's SL or Target.
            
            Request Body:
            {
                "stoploss": 215.00,
                "target": 320.00
            }
            """
            try:
                body = request.json
                new_sl = body.get("stoploss")
                new_target = body.get("target")
                
                # Check paper positions
                for pos_id, pos in self.paper_positions.items():
                    if pos.get("order_id") == order_id:
                        if new_sl:
                            pos["stoploss"] = float(new_sl)
                        if new_target:
                            pos["target"] = float(new_target)
                        return jsonify({
                            "status": "MODIFIED",
                            "order_id": order_id,
                            "stoploss": pos.get("stoploss"),
                            "target": pos.get("target")
                        })
                
                return jsonify({
                    "status": "NOT_FOUND",
                    "message": f"Order {order_id} not found"
                }), 404
                
            except Exception as e:
                return jsonify({"status": "ERROR", "message": str(e)}), 500

        # ===== CANCEL ORDER =====
        @self.blueprint.route("/cancel/<order_id>", methods=["POST"])
        def cancel_order(order_id):
            """Cancel a pending order."""
            try:
                # Paper orders
                if order_id in self.paper_orders:
                    order = self.paper_orders[order_id]
                    if order.get("status") == "PENDING":
                        order["status"] = "CANCELLED"
                        return jsonify({
                            "status": "CANCELLED",
                            "order_id": order_id
                        })
                    return jsonify({
                        "status": "ERROR",
                        "message": f"Order {order_id} cannot be cancelled (status: {order.get('status')})"
                    }), 400
                
                # Live orders
                if self.market_feed and hasattr(self.market_feed, 'kite'):
                    try:
                        self.market_feed.kite.cancel_order(
                            variety="regular",
                            order_id=order_id
                        )
                        return jsonify({
                            "status": "CANCELLED",
                            "order_id": order_id
                        })
                    except Exception as e:
                        return jsonify({
                            "status": "ERROR",
                            "message": str(e)
                        }), 400
                
                return jsonify({
                    "status": "NOT_FOUND",
                    "message": f"Order {order_id} not found"
                }), 404
                
            except Exception as e:
                return jsonify({"status": "ERROR", "message": str(e)}), 500

        # ===== ORDER HISTORY =====
        @self.blueprint.route("/history", methods=["GET"])
        def order_history():
            """Get order/trade history."""
            try:
                limit = int(request.args.get("limit", 50))
                
                trades = []
                
                # From trade logger
                if self.trade_logger:
                    logged_trades = self.trade_logger.get_recent_trades(limit)
                    trades.extend(logged_trades)
                
                # From paper orders
                paper_trades = list(self.paper_orders.values())
                trades.extend(paper_trades)
                
                # Sort by timestamp descending
                trades.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                
                return jsonify({
                    "trades": trades[:limit],
                    "count": len(trades[:limit])
                })
                
            except Exception as e:
                return jsonify({"status": "ERROR", "message": str(e)}), 500

        # ===== TRADING MODE =====
        @self.blueprint.route("/mode", methods=["GET"])
        def get_trading_mode():
            """Get current trading mode."""
            return jsonify({
                "mode": "paper" if self.order_router.paper_trading_mode else "live",
                "paper_positions": len(self.paper_positions),
                "ip_compliance": self._check_sebi_compliance() if self.ip_compliance else None
            })

        @self.blueprint.route("/mode", methods=["POST"])
        def set_trading_mode():
            """
            Set trading mode.
            
            Request Body:
            { "mode": "paper" | "live" }
            """
            try:
                body = request.json
                mode = body.get("mode", "paper").lower()
                
                if mode == "live":
                    # Check SEBI compliance before allowing live mode
                    ip_check = self._check_sebi_compliance()
                    if not ip_check["allowed"]:
                        return jsonify({
                            "status": "ERROR",
                            "message": "Cannot enable live trading: " + ip_check.get("reason", "IP not registered"),
                            "ip_compliance": ip_check
                        }), 403
                
                self.order_router.paper_trading_mode = (mode == "paper")
                
                return jsonify({
                    "status": "OK",
                    "mode": mode,
                    "message": f"Trading mode set to {mode.upper()}"
                })
                
            except Exception as e:
                return jsonify({"status": "ERROR", "message": str(e)}), 500

    # ===== HELPER METHODS =====

    def _get_ltp(self, symbol):
        """Get last traded price for a symbol."""
        try:
            if self.market_feed:
                # Try from live feed
                if hasattr(self.market_feed, 'get_spot_price'):
                    return self.market_feed.get_spot_price(symbol)
                
                # Try from Kite quote
                if hasattr(self.market_feed, 'kite'):
                    quote = self.market_feed.kite.quote([f"NFO:{symbol}"])
                    for key, data in quote.items():
                        return data.get("last_price")
            return None
        except Exception as e:
            print(f"⚠️ LTP fetch error for {symbol}: {e}")
            return None

    def _check_sebi_compliance(self):
        """Check SEBI IP compliance."""
        if not self.ip_compliance:
            return {"allowed": True, "reason": "IP compliance not configured"}
        return self.ip_compliance.validate_order_ip()

    def _execute_paper_order(self, symbol, exchange, side, qty, order_type, 
                             entry_price, stoploss, target):
        """Execute a paper (simulated) order."""
        order_id = f"PAP-{uuid.uuid4().hex[:8].upper()}"
        timestamp = datetime.now().isoformat()
        
        # Simulate slight slippage for market orders
        if order_type == "MARKET":
            slippage = entry_price * 0.0005  # 0.05% slippage
            fill_price = entry_price + slippage if side == "BUY" else entry_price - slippage
        else:
            fill_price = entry_price
        
        order = {
            "order_id": order_id,
            "symbol": symbol,
            "exchange": exchange,
            "side": side,
            "qty": qty,
            "order_type": order_type,
            "entry_price": entry_price,
            "fill_price": round(fill_price, 2),
            "stoploss": stoploss,
            "target": target,
            "status": "EXECUTED",
            "mode": "paper",
            "timestamp": timestamp
        }
        
        # Store order
        self.paper_orders[order_id] = order
        
        # Create/update position
        pos_key = f"{symbol}_{side}"
        if pos_key in self.paper_positions:
            # Average into existing position
            pos = self.paper_positions[pos_key]
            total_qty = pos["qty"] + qty
            avg_price = ((pos["avg_price"] * pos["qty"]) + (fill_price * qty)) / total_qty
            pos["qty"] = total_qty
            pos["avg_price"] = round(avg_price, 2)
            pos["stoploss"] = stoploss or pos.get("stoploss")
            pos["target"] = target or pos.get("target")
        else:
            # New position
            self.paper_positions[pos_key] = {
                "position_id": f"POS-{uuid.uuid4().hex[:8].upper()}",
                "order_id": order_id,
                "symbol": symbol,
                "exchange": exchange,
                "side": side,
                "qty": qty,
                "avg_price": round(fill_price, 2),
                "stoploss": stoploss,
                "target": target,
                "ltp": fill_price,
                "pnl": 0,
                "pnl_pct": 0,
                "timestamp": timestamp
            }
        
        # Log trade
        if self.trade_logger:
            self.trade_logger.log_trade(order)
        
        print(f"📝 Paper Order: {side} {qty} {symbol} @ {fill_price}")
        
        return order

    def _execute_live_order(self, symbol, exchange, side, qty, order_type,
                            entry_price, stoploss, target):
        """Execute a live order via Zerodha/Kite."""
        try:
            if not self.market_feed or not hasattr(self.market_feed, 'kite'):
                return {
                    "status": "ERROR",
                    "message": "Kite connection not available for live trading"
                }
            
            kite = self.market_feed.kite
            
            # Map side to Kite transaction type
            transaction_type = kite.TRANSACTION_TYPE_BUY if side == "BUY" else kite.TRANSACTION_TYPE_SELL
            
            # Map order type
            kite_order_type = kite.ORDER_TYPE_MARKET if order_type == "MARKET" else kite.ORDER_TYPE_LIMIT
            
            # Place main order
            order_id = kite.place_order(
                variety=kite.VARIETY_REGULAR,
                exchange=exchange,
                tradingsymbol=symbol,
                transaction_type=transaction_type,
                quantity=qty,
                product=kite.PRODUCT_MIS,  # Intraday
                order_type=kite_order_type,
                price=entry_price if order_type == "LIMIT" else None
            )
            
            result = {
                "order_id": order_id,
                "symbol": symbol,
                "exchange": exchange,
                "side": side,
                "qty": qty,
                "order_type": order_type,
                "entry_price": entry_price,
                "stoploss": stoploss,
                "target": target,
                "status": "PLACED",
                "mode": "live",
                "timestamp": datetime.now().isoformat()
            }
            
            # Place SL order if specified
            if stoploss:
                try:
                    sl_side = kite.TRANSACTION_TYPE_SELL if side == "BUY" else kite.TRANSACTION_TYPE_BUY
                    sl_order_id = kite.place_order(
                        variety=kite.VARIETY_REGULAR,
                        exchange=exchange,
                        tradingsymbol=symbol,
                        transaction_type=sl_side,
                        quantity=qty,
                        product=kite.PRODUCT_MIS,
                        order_type=kite.ORDER_TYPE_SL,
                        trigger_price=stoploss,
                        price=stoploss
                    )
                    result["sl_order_id"] = sl_order_id
                except Exception as e:
                    print(f"⚠️ SL order failed: {e}")
            
            # Log trade
            if self.trade_logger:
                self.trade_logger.log_trade(result)
            
            print(f"🔴 LIVE Order: {side} {qty} {symbol} - Order ID: {order_id}")
            
            return result
            
        except Exception as e:
            print(f"❌ Live order error: {e}")
            return {
                "status": "ERROR",
                "message": str(e)
            }

    def _get_live_positions(self):
        """Get live positions from Kite."""
        positions = []
        try:
            if self.market_feed and hasattr(self.market_feed, 'kite'):
                kite_positions = self.market_feed.kite.positions()
                
                for pos in kite_positions.get("day", []):
                    if pos.get("quantity", 0) != 0:
                        qty = pos["quantity"]
                        avg_price = pos.get("average_price", 0)
                        ltp = pos.get("last_price", avg_price)
                        pnl = pos.get("pnl", 0)
                        
                        positions.append({
                            "position_id": f"LIVE-{pos.get('tradingsymbol')}",
                            "symbol": pos.get("tradingsymbol"),
                            "exchange": pos.get("exchange"),
                            "side": "BUY" if qty > 0 else "SELL",
                            "qty": abs(qty),
                            "avg_price": avg_price,
                            "ltp": ltp,
                            "pnl": pnl,
                            "pnl_pct": (pnl / (avg_price * abs(qty)) * 100) if avg_price else 0
                        })
        except Exception as e:
            print(f"⚠️ Live positions fetch error: {e}")
        
        return positions

    def _calculate_pnl(self, position, ltp):
        """Calculate P&L for a position."""
        qty = position.get("qty", 0)
        avg_price = position.get("avg_price", 0)
        side = position.get("side", "BUY")
        
        if side == "BUY":
            return (ltp - avg_price) * qty
        else:
            return (avg_price - ltp) * qty

    def _square_off_paper(self, position_id, exit_qty=None):
        """Square off a paper position."""
        for pos_key, pos in list(self.paper_positions.items()):
            if pos.get("position_id") == position_id:
                symbol = pos["symbol"]
                ltp = self._get_ltp(symbol) or pos.get("ltp", pos["avg_price"])
                
                exit_qty = exit_qty or pos["qty"]
                pnl = self._calculate_pnl(pos, ltp)
                
                # Create exit order
                exit_side = "SELL" if pos["side"] == "BUY" else "BUY"
                exit_order = {
                    "order_id": f"EXIT-{uuid.uuid4().hex[:8].upper()}",
                    "symbol": symbol,
                    "side": exit_side,
                    "qty": exit_qty,
                    "entry_price": ltp,
                    "fill_price": ltp,
                    "status": "EXECUTED",
                    "mode": "paper",
                    "pnl": round(pnl, 2),
                    "timestamp": datetime.now().isoformat()
                }
                
                self.paper_orders[exit_order["order_id"]] = exit_order
                
                # Remove or reduce position
                if exit_qty >= pos["qty"]:
                    del self.paper_positions[pos_key]
                else:
                    pos["qty"] -= exit_qty
                
                # Log trade
                if self.trade_logger:
                    self.trade_logger.log_trade(exit_order)
                
                print(f"📝 Paper Square-off: {exit_side} {exit_qty} {symbol} @ {ltp}, P&L: {pnl:.2f}")
                
                return {
                    "status": "SQUARED_OFF",
                    "order": exit_order,
                    "pnl": round(pnl, 2)
                }
        
        return {"status": "NOT_FOUND", "message": f"Position {position_id} not found"}

    def _square_off_live(self, position_id, exit_qty=None):
        """Square off a live position."""
        try:
            if not self.market_feed or not hasattr(self.market_feed, 'kite'):
                return {"status": "ERROR", "message": "Kite not available"}
            
            # Extract symbol from position_id (format: LIVE-SYMBOL)
            symbol = position_id.replace("LIVE-", "")
            
            kite = self.market_feed.kite
            positions = kite.positions()
            
            for pos in positions.get("day", []):
                if pos.get("tradingsymbol") == symbol and pos.get("quantity") != 0:
                    qty = exit_qty or abs(pos["quantity"])
                    side = kite.TRANSACTION_TYPE_SELL if pos["quantity"] > 0 else kite.TRANSACTION_TYPE_BUY
                    
                    order_id = kite.place_order(
                        variety=kite.VARIETY_REGULAR,
                        exchange=pos.get("exchange", "NFO"),
                        tradingsymbol=symbol,
                        transaction_type=side,
                        quantity=qty,
                        product=kite.PRODUCT_MIS,
                        order_type=kite.ORDER_TYPE_MARKET
                    )
                    
                    return {
                        "status": "SQUARED_OFF",
                        "order_id": order_id,
                        "symbol": symbol,
                        "qty": qty
                    }
            
            return {"status": "NOT_FOUND", "message": f"Position {position_id} not found"}
            
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    def get_blueprint(self):
        """Return Flask blueprint for registration."""
        return self.blueprint
