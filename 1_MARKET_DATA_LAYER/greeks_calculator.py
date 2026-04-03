"""
Options Greeks Calculator
=========================
Calculates real-time Greeks (Delta, Gamma, Theta, Vega, Rho) 
using Black-Scholes model from Zerodha option chain data.

Formulas:
- Delta: Rate of change of option price with respect to underlying
- Gamma: Rate of change of delta with respect to underlying  
- Theta: Rate of change of option price with respect to time
- Vega: Rate of change of option price with respect to volatility
- IV: Implied volatility backed out from market price
"""

import math
from datetime import datetime, date
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger("GREEKS_CALCULATOR")

# Constants
TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE = 0.07  # 7% Indian risk-free rate (approximate)


def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


class GreeksCalculator:
    """
    Calculate option Greeks from market data.
    """
    
    def __init__(self, risk_free_rate: float = RISK_FREE_RATE):
        self.risk_free_rate = risk_free_rate
        self.iv_cache = {}  # Cache IV calculations
        
    def calculate_greeks(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,  # In years
        volatility: float,  # As decimal (0.20 = 20%)
        option_type: str = "CE",  # CE or PE
        risk_free_rate: float = None
    ) -> Dict[str, float]:
        """
        Calculate all Greeks for an option.
        
        Args:
            spot_price: Current price of underlying
            strike_price: Strike price of option
            time_to_expiry: Time to expiry in years
            volatility: Implied volatility as decimal
            option_type: "CE" for call, "PE" for put
            risk_free_rate: Risk-free interest rate
            
        Returns:
            Dict with delta, gamma, theta, vega, rho
        """
        r = risk_free_rate or self.risk_free_rate
        S = spot_price
        K = strike_price
        T = max(time_to_expiry, 0.001)  # Avoid division by zero
        sigma = max(volatility, 0.001)
        
        try:
            # Calculate d1 and d2
            d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            
            # Common terms
            sqrt_T = math.sqrt(T)
            exp_neg_rT = math.exp(-r * T)
            nd1 = norm_cdf(d1)
            nd2 = norm_cdf(d2)
            npd1 = norm_pdf(d1)
            
            if option_type.upper() == "CE":
                # Call option Greeks
                delta = nd1
                theta = (-(S * npd1 * sigma) / (2 * sqrt_T) 
                        - r * K * exp_neg_rT * nd2) / TRADING_DAYS_PER_YEAR
            else:
                # Put option Greeks
                delta = nd1 - 1
                nd2_neg = norm_cdf(-d2)
                theta = (-(S * npd1 * sigma) / (2 * sqrt_T) 
                        + r * K * exp_neg_rT * nd2_neg) / TRADING_DAYS_PER_YEAR
            
            # Gamma (same for call and put)
            gamma = npd1 / (S * sigma * sqrt_T)
            
            # Vega (same for call and put) - per 1% move in IV
            vega = S * sqrt_T * npd1 / 100
            
            # Rho
            if option_type.upper() == "CE":
                rho = K * T * exp_neg_rT * nd2 / 100
            else:
                rho = -K * T * exp_neg_rT * norm_cdf(-d2) / 100
            
            return {
                "delta": round(delta, 4),
                "gamma": round(gamma, 6),
                "theta": round(theta, 2),
                "vega": round(vega, 2),
                "rho": round(rho, 2),
                "d1": round(d1, 4),
                "d2": round(d2, 4)
            }
            
        except Exception as e:
            logger.error(f"Greeks calculation error: {e}")
            return {
                "delta": 0.5 if option_type == "CE" else -0.5,
                "gamma": 0.01,
                "theta": -10,
                "vega": 50,
                "rho": 0
            }
    
    def calculate_iv(
        self,
        option_price: float,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        option_type: str = "CE",
        risk_free_rate: float = None,
        max_iterations: int = 100,
        tolerance: float = 0.0001
    ) -> float:
        """
        Calculate implied volatility using Newton-Raphson method.
        
        Args:
            option_price: Current market price of the option
            spot_price: Current price of underlying
            strike_price: Strike price
            time_to_expiry: Time to expiry in years
            option_type: "CE" or "PE"
            
        Returns:
            Implied volatility as decimal
        """
        r = risk_free_rate or self.risk_free_rate
        S = spot_price
        K = strike_price
        T = max(time_to_expiry, 0.001)
        market_price = option_price
        
        # Check cache
        cache_key = f"{S:.0f}_{K:.0f}_{T:.4f}_{option_type}_{market_price:.2f}"
        if cache_key in self.iv_cache:
            return self.iv_cache[cache_key]
        
        # Initial guess based on rough approximation
        sigma = 0.20  # Start with 20% IV
        
        for _ in range(max_iterations):
            # Calculate theoretical price
            bs_price = self._black_scholes_price(S, K, T, r, sigma, option_type)
            
            # Calculate vega for Newton-Raphson
            d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            vega = S * math.sqrt(T) * norm_pdf(d1)
            
            if vega < 0.00001:
                break
                
            # Newton-Raphson update
            price_diff = bs_price - market_price
            
            if abs(price_diff) < tolerance:
                break
                
            sigma = sigma - price_diff / vega
            
            # Bound sigma to reasonable range
            sigma = max(0.01, min(sigma, 3.0))
        
        # Cache result
        self.iv_cache[cache_key] = sigma
        
        # Limit cache size
        if len(self.iv_cache) > 1000:
            # Remove oldest entries
            keys = list(self.iv_cache.keys())[:500]
            for k in keys:
                del self.iv_cache[k]
        
        return sigma
    
    def _black_scholes_price(
        self,
        S: float,
        K: float,
        T: float,
        r: float,
        sigma: float,
        option_type: str
    ) -> float:
        """Calculate Black-Scholes option price."""
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        
        if option_type.upper() == "CE":
            return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
        else:
            return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
    
    def days_to_expiry(self, expiry_date) -> int:
        """Calculate days to expiry from expiry date."""
        if isinstance(expiry_date, str):
            expiry_date = datetime.fromisoformat(expiry_date).date()
        elif isinstance(expiry_date, datetime):
            expiry_date = expiry_date.date()
        
        today = date.today()
        return max((expiry_date - today).days, 0)
    
    def time_to_expiry_years(self, expiry_date) -> float:
        """Convert expiry date to time in years."""
        dte = self.days_to_expiry(expiry_date)
        return dte / TRADING_DAYS_PER_YEAR


class ZerodhaGreeksIntegration:
    """
    Integrates Greeks calculation with Zerodha option chain data.
    """
    
    def __init__(self, market_feed=None):
        self.market_feed = market_feed
        self.calculator = GreeksCalculator()
        self.latest_greeks = {}
        self.atm_greeks = {}
        
    def calculate_chain_greeks(self, symbol: str, spot_price: float = None) -> Dict:
        """
        Calculate Greeks for entire option chain.
        
        Args:
            symbol: Underlying symbol (e.g., "BANKNIFTY")
            spot_price: Current spot price (fetched if not provided)
            
        Returns:
            Dict with ATM Greeks and chain Greeks
        """
        if not self.market_feed:
            return self._get_default_greeks()
        
        try:
            # Get option chain from Zerodha
            chain = self.market_feed.get_option_chain(symbol, spot_price)
            
            if not chain or not chain.get("strikes"):
                return self._get_default_greeks()
            
            spot = chain.get("spot_price") or spot_price
            expiry = chain.get("expiry")
            atm_strike = chain.get("atm_strike")
            strikes = chain.get("strikes", [])
            
            if not spot or not expiry:
                return self._get_default_greeks()
            
            # Calculate time to expiry
            T = self.calculator.time_to_expiry_years(expiry)
            dte = self.calculator.days_to_expiry(expiry)
            
            # Process each strike
            chain_greeks = []
            atm_call_greeks = None
            atm_put_greeks = None
            total_call_oi = 0
            total_put_oi = 0
            iv_values = []
            
            for strike_data in strikes:
                strike = strike_data.get("strike")
                call_ltp = strike_data.get("call_ltp", 0)
                put_ltp = strike_data.get("put_ltp", 0)
                call_oi = strike_data.get("call_oi", 0)
                put_oi = strike_data.get("put_oi", 0)
                
                total_call_oi += call_oi
                total_put_oi += put_oi
                
                # Calculate IV for call
                call_iv = 0.20  # Default
                if call_ltp > 0:
                    try:
                        call_iv = self.calculator.calculate_iv(
                            call_ltp, spot, strike, T, "CE"
                        )
                        iv_values.append(call_iv)
                    except Exception as e:
                        logger.debug(f"Call IV calc failed for strike {strike}: {e}")
                
                # Calculate IV for put
                put_iv = 0.20  # Default
                if put_ltp > 0:
                    try:
                        put_iv = self.calculator.calculate_iv(
                            put_ltp, spot, strike, T, "PE"
                        )
                        iv_values.append(put_iv)
                    except Exception as e:
                        logger.debug(f"Put IV calc failed for strike {strike}: {e}")
                
                # Calculate Greeks for call
                call_greeks = self.calculator.calculate_greeks(
                    spot, strike, T, call_iv, "CE"
                )
                
                # Calculate Greeks for put
                put_greeks = self.calculator.calculate_greeks(
                    spot, strike, T, put_iv, "PE"
                )
                
                strike_greeks = {
                    "strike": strike,
                    "call": {
                        "ltp": call_ltp,
                        "oi": call_oi,
                        "iv": round(call_iv * 100, 2),
                        **call_greeks
                    },
                    "put": {
                        "ltp": put_ltp,
                        "oi": put_oi,
                        "iv": round(put_iv * 100, 2),
                        **put_greeks
                    }
                }
                
                chain_greeks.append(strike_greeks)
                
                # Store ATM Greeks
                if strike == atm_strike:
                    atm_call_greeks = call_greeks
                    atm_put_greeks = put_greeks
                    atm_call_greeks["iv"] = round(call_iv * 100, 2)
                    atm_put_greeks["iv"] = round(put_iv * 100, 2)
            
            # Calculate aggregate metrics
            avg_iv = sum(iv_values) / len(iv_values) * 100 if iv_values else 20.0
            pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0
            
            # Net Greeks (weighted by OI)
            net_delta = 0
            net_gamma = 0
            net_theta = 0
            net_vega = 0
            
            for sg in chain_greeks:
                call_weight = sg["call"]["oi"] / max(total_call_oi, 1)
                put_weight = sg["put"]["oi"] / max(total_put_oi, 1)
                
                net_delta += sg["call"]["delta"] * call_weight + sg["put"]["delta"] * put_weight
                net_gamma += (sg["call"]["gamma"] + sg["put"]["gamma"]) * (call_weight + put_weight) / 2
                net_theta += sg["call"]["theta"] * call_weight + sg["put"]["theta"] * put_weight
                net_vega += (sg["call"]["vega"] + sg["put"]["vega"]) * (call_weight + put_weight) / 2
            
            # Build result
            result = {
                "symbol": symbol,
                "spot_price": spot,
                "expiry": expiry,
                "dte": dte,
                "atm_strike": atm_strike,
                
                # ATM Greeks (use call for now)
                "delta": atm_call_greeks.get("delta", 0.5) if atm_call_greeks else 0.5,
                "gamma": atm_call_greeks.get("gamma", 0.01) if atm_call_greeks else 0.01,
                "theta": atm_call_greeks.get("theta", -30) if atm_call_greeks else -30,
                "vega": atm_call_greeks.get("vega", 100) if atm_call_greeks else 100,
                
                # IV metrics
                "atm_iv": atm_call_greeks.get("iv", 20) if atm_call_greeks else 20,
                "avg_iv": round(avg_iv, 2),
                "iv_percentile": self._calculate_iv_percentile(avg_iv),
                
                # Market metrics
                "pcr_oi": round(pcr, 2),
                "total_call_oi": total_call_oi,
                "total_put_oi": total_put_oi,
                
                # Full chain
                "chain": chain_greeks,
                
                "timestamp": datetime.now().isoformat()
            }
            
            self.latest_greeks[symbol] = result
            self.atm_greeks = {
                "delta": result["delta"],
                "gamma": result["gamma"],
                "theta": result["theta"],
                "vega": result["vega"],
                "iv": result["atm_iv"],
                "iv_percentile": result["iv_percentile"]
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Chain Greeks calculation error: {e}")
            return self._get_default_greeks()
    
    def _calculate_iv_percentile(self, current_iv: float) -> float:
        """
        Calculate IV percentile based on historical IV ranges for Indian indices.
        
        Uses realistic historical IV ranges:
        - NIFTY 50: Typically ranges from 10% (calm markets) to 35%+ (volatile/crisis)
        - Historical data shows NIFTY IV:
          - 10th percentile: ~11%
          - 25th percentile: ~13%
          - 50th percentile: ~16%
          - 75th percentile: ~22%
          - 90th percentile: ~28%
          - 95th percentile: ~32%
        
        When IV is 25%, it's in the top 10-15% historically (around 85-90 percentile)
        """
        # Historical IV distribution for Indian indices (based on VIX data)
        # Format: (iv_level, percentile)
        historical_percentiles = [
            (10, 5),    # 10% IV = 5th percentile (very calm)
            (12, 15),   # 12% IV = 15th percentile
            (14, 30),   # 14% IV = 30th percentile
            (16, 50),   # 16% IV = 50th percentile (median)
            (18, 65),   # 18% IV = 65th percentile
            (20, 75),   # 20% IV = 75th percentile
            (22, 82),   # 22% IV = 82th percentile
            (24, 88),   # 24% IV = 88th percentile
            (26, 93),   # 26% IV = 93rd percentile (high IV)
            (28, 96),   # 28% IV = 96th percentile
            (30, 98),   # 30% IV = 98th percentile
            (35, 99),   # 35% IV = 99th percentile (crisis level)
            (45, 100),  # 45%+ IV = 100th percentile (extreme)
        ]
        
        # Handle edge cases
        if current_iv <= historical_percentiles[0][0]:
            return historical_percentiles[0][1]
        if current_iv >= historical_percentiles[-1][0]:
            return historical_percentiles[-1][1]
        
        # Linear interpolation between known points
        for i in range(len(historical_percentiles) - 1):
            iv_low, pct_low = historical_percentiles[i]
            iv_high, pct_high = historical_percentiles[i + 1]
            
            if iv_low <= current_iv <= iv_high:
                # Linear interpolation
                ratio = (current_iv - iv_low) / (iv_high - iv_low)
                percentile = pct_low + ratio * (pct_high - pct_low)
                return round(percentile, 1)
        
        return 50.0  # Fallback
    
    def _get_default_greeks(self) -> Dict:
        """Return default Greeks when data is unavailable."""
        return {
            "symbol": "UNKNOWN",
            "spot_price": 0,
            "delta": 0.5,
            "gamma": 0.02,
            "theta": -30,
            "vega": 100,
            "atm_iv": 20,
            "iv_percentile": 50,
            "pcr_oi": 1.0,
            "dte": 7,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_atm_greeks(self) -> Dict:
        """Get cached ATM Greeks."""
        return self.atm_greeks or {
            "delta": 0.5,
            "gamma": 0.02,
            "theta": -30,
            "vega": 100,
            "iv": 20,
            "iv_percentile": 50
        }


# Singleton instance
_greeks_integration = None

def get_greeks_integration(market_feed=None) -> ZerodhaGreeksIntegration:
    """Get or create the global Greeks integration."""
    global _greeks_integration
    if _greeks_integration is None:
        _greeks_integration = ZerodhaGreeksIntegration(market_feed)
    elif market_feed and _greeks_integration.market_feed is None:
        _greeks_integration.market_feed = market_feed
    return _greeks_integration
