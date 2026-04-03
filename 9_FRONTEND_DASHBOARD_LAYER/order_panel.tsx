/**
 * Order Panel - Manual Buy/Sell Execution Component
 * Supports Paper Trading and Live Trading modes with full order form.
 */

import React, { useState, useEffect } from "react"
import { spaceTheme } from "./theme"
import { getBackendBaseUrl } from "./api_service"

export type OrderSide = "BUY" | "SELL"
export type OrderType = "MARKET" | "LIMIT"
export type TradingMode = "paper" | "live"

export type OrderRequest = {
    symbol: string
    exchange: string
    side: OrderSide
    qty: number
    order_type: OrderType
    price?: number
    stoploss?: number
    target?: number
    mode: TradingMode
}

export type OrderResponse = {
    order_id?: string
    status: string
    symbol?: string
    side?: string
    qty?: number
    fill_price?: number
    message?: string
    stoploss?: number
    target?: number
    mode?: string
}

export type Position = {
    position_id: string
    symbol: string
    exchange?: string
    side: string
    qty: number
    avg_price: number
    ltp?: number
    pnl?: number
    pnl_pct?: number
    stoploss?: number
    target?: number
    mode: string
}

type PrefilledTrade = {
    symbol: string
    action: string
    entry: number
    target: number
    stoploss: number
    qty: number
    riskAmount: number
}

type OrderPanelProps = {
    selectedSymbol?: string
    selectedStrike?: number
    spotPrice?: number
    onOrderPlaced?: (order: OrderResponse) => void
    prefilledTrade?: PrefilledTrade | null
}

const OrderPanel: React.FC<OrderPanelProps> = ({
    selectedSymbol,
    // selectedStrike and spotPrice reserved for future use
    onOrderPlaced,
    prefilledTrade
}) => {
    // Form state
    const [symbol, setSymbol] = useState(selectedSymbol || "")
    const [side, setSide] = useState<OrderSide>("BUY")
    const [qty, setQty] = useState<number>(15)
    const [orderType, setOrderType] = useState<OrderType>("MARKET")
    const [price, setPrice] = useState<number | undefined>(undefined)
    const [stoploss, setStoploss] = useState<number | undefined>(undefined)
    const [target, setTarget] = useState<number | undefined>(undefined)
    const [mode, setMode] = useState<TradingMode>("paper")
    
    // UI state
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState<string | null>(null)
    const [showConfirm, setShowConfirm] = useState(false)
    const [ipStatus, setIpStatus] = useState<{ allowed: boolean; reason?: string } | null>(null)

    // Update symbol when prop changes
    useEffect(() => {
        if (selectedSymbol) {
            setSymbol(selectedSymbol)
        }
    }, [selectedSymbol])
    
    // Apply prefilled trade data from signal panel
    useEffect(() => {
        if (prefilledTrade) {
            setSymbol(prefilledTrade.symbol)
            setSide(prefilledTrade.action === "BUY" ? "BUY" : "SELL")
            setQty(prefilledTrade.qty)
            setPrice(prefilledTrade.entry)
            setStoploss(prefilledTrade.stoploss)
            setTarget(prefilledTrade.target)
            setSuccess(`📊 Signal loaded: ${prefilledTrade.action} ${prefilledTrade.symbol} @ ₹${prefilledTrade.entry.toFixed(2)}`)
        }
    }, [prefilledTrade])

    // Check IP compliance status
    useEffect(() => {
        const checkIp = async () => {
            try {
                const res = await fetch(`${getBackendBaseUrl()}/api/ip-validate`)
                const data = await res.json()
                setIpStatus(data)
            } catch (e) {
                console.error("IP check failed:", e)
            }
        }
        checkIp()
        const interval = setInterval(checkIp, 60000) // Check every minute
        return () => clearInterval(interval)
    }, [])

    const handleSubmit = async () => {
        setError(null)
        setSuccess(null)

        // Validation
        if (!symbol.trim()) {
            setError("Symbol is required")
            return
        }
        if (qty <= 0) {
            setError("Quantity must be greater than 0")
            return
        }
        if (orderType === "LIMIT" && (!price || price <= 0)) {
            setError("Price required for LIMIT orders")
            return
        }

        // Live mode confirmation
        if (mode === "live" && !showConfirm) {
            setShowConfirm(true)
            return
        }

        setShowConfirm(false)
        setLoading(true)

        try {
            const orderRequest: OrderRequest = {
                symbol: symbol.trim().toUpperCase(),
                exchange: "NFO",
                side,
                qty,
                order_type: orderType,
                price: orderType === "LIMIT" ? price : undefined,
                stoploss: stoploss || undefined,
                target: target || undefined,
                mode
            }

            const response = await fetch(`${getBackendBaseUrl()}/api/order/place`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(orderRequest)
            })

            const data: OrderResponse = await response.json()

            if (response.ok && data.status === "EXECUTED") {
                setSuccess(`✅ Order ${data.order_id} executed @ ₹${data.fill_price?.toFixed(2)}`)
                onOrderPlaced?.(data)
                
                // Reset form partially
                setStoploss(undefined)
                setTarget(undefined)
            } else if (data.status === "PLACED") {
                setSuccess(`📤 Order ${data.order_id} placed successfully`)
                onOrderPlaced?.(data)
            } else {
                setError(data.message || "Order failed")
            }
        } catch (e: any) {
            setError(e.message || "Network error")
        } finally {
            setLoading(false)
        }
    }

    const handleModeChange = (newMode: TradingMode) => {
        if (newMode === "live" && ipStatus && !ipStatus.allowed) {
            // Show warning but allow switching - user can still try (order might be rejected by Zerodha)
            setError(`⚠️ Warning: ${ipStatus.reason}. Orders may be rejected by Zerodha.`)
        } else {
            setError(null)
        }
        setMode(newMode)
    }

    return (
        <div style={styles.container}>
            {/* Header with Mode Toggle */}
            <div style={styles.header}>
                <h3 style={styles.title}>📝 Place Order</h3>
                <div style={styles.modeToggle}>
                    <button
                        style={mode === "paper" ? styles.modeButtonActive : styles.modeButton}
                        onClick={() => handleModeChange("paper")}
                    >
                        📄 Paper
                    </button>
                    <button
                        style={mode === "live" ? styles.modeButtonLive : styles.modeButton}
                        onClick={() => handleModeChange("live")}
                        title={ipStatus && !ipStatus.allowed ? `Warning: ${ipStatus.reason}` : "Live Trading - Real Money"}
                    >
                        🔴 Live
                    </button>
                </div>
            </div>

            {/* IP Warning - Show when Live mode is selected but IP not registered */}
            {ipStatus && !ipStatus.allowed && (
                <div style={styles.ipWarning}>
                    ⚠️ IP Check: {ipStatus.reason || "IP not registered"}
                    <br/>
                    <small style={{opacity: 0.8}}>
                        {mode === "live" ? "Orders may be blocked by Zerodha" : "Register IP before going Live"}
                    </small>
                </div>
            )}

            {/* Symbol Input */}
            <div style={styles.formGroup}>
                <label style={styles.label}>Symbol</label>
                <input
                    type="text"
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                    placeholder="e.g., BANKNIFTY24APR52000CE"
                    style={styles.input}
                />
            </div>

            {/* Side Toggle */}
            <div style={styles.formGroup}>
                <label style={styles.label}>Side</label>
                <div style={styles.sideToggle}>
                    <button
                        style={side === "BUY" ? styles.buyButtonActive : styles.sideButton}
                        onClick={() => setSide("BUY")}
                    >
                        BUY
                    </button>
                    <button
                        style={side === "SELL" ? styles.sellButtonActive : styles.sideButton}
                        onClick={() => setSide("SELL")}
                    >
                        SELL
                    </button>
                </div>
            </div>

            {/* Quantity */}
            <div style={styles.formGroup}>
                <label style={styles.label}>Quantity</label>
                <input
                    type="number"
                    value={qty}
                    onChange={(e) => setQty(Math.max(1, parseInt(e.target.value) || 0))}
                    min={1}
                    style={styles.input}
                />
                <div style={styles.qtyPresets}>
                    {[15, 25, 50, 75, 100].map(q => (
                        <button
                            key={q}
                            style={styles.qtyPreset}
                            onClick={() => setQty(q)}
                        >
                            {q}
                        </button>
                    ))}
                </div>
            </div>

            {/* Order Type */}
            <div style={styles.formGroup}>
                <label style={styles.label}>Order Type</label>
                <div style={styles.sideToggle}>
                    <button
                        style={orderType === "MARKET" ? styles.typeButtonActive : styles.sideButton}
                        onClick={() => setOrderType("MARKET")}
                    >
                        Market
                    </button>
                    <button
                        style={orderType === "LIMIT" ? styles.typeButtonActive : styles.sideButton}
                        onClick={() => setOrderType("LIMIT")}
                    >
                        Limit
                    </button>
                </div>
            </div>

            {/* Limit Price */}
            {orderType === "LIMIT" && (
                <div style={styles.formGroup}>
                    <label style={styles.label}>Limit Price</label>
                    <input
                        type="number"
                        value={price || ""}
                        onChange={(e) => setPrice(parseFloat(e.target.value) || undefined)}
                        placeholder="Enter price"
                        step={0.05}
                        style={styles.input}
                    />
                </div>
            )}

            {/* Stoploss */}
            <div style={styles.formGroup}>
                <label style={styles.label}>Stoploss (Optional)</label>
                <input
                    type="number"
                    value={stoploss || ""}
                    onChange={(e) => setStoploss(parseFloat(e.target.value) || undefined)}
                    placeholder="SL Price"
                    step={0.05}
                    style={styles.input}
                />
            </div>

            {/* Target */}
            <div style={styles.formGroup}>
                <label style={styles.label}>Target (Optional)</label>
                <input
                    type="number"
                    value={target || ""}
                    onChange={(e) => setTarget(parseFloat(e.target.value) || undefined)}
                    placeholder="Target Price"
                    step={0.05}
                    style={styles.input}
                />
            </div>

            {/* Error/Success Messages */}
            {error && <div style={styles.error}>{error}</div>}
            {success && <div style={styles.success}>{success}</div>}

            {/* Live Confirmation Dialog */}
            {showConfirm && mode === "live" && (
                <div style={styles.confirmBox}>
                    <p style={styles.confirmText}>
                        ⚠️ <strong>LIVE ORDER</strong><br />
                        {side} {qty} {symbol}<br />
                        This will place a REAL order with Zerodha.
                    </p>
                    <div style={styles.confirmButtons}>
                        <button style={styles.cancelButton} onClick={() => setShowConfirm(false)}>
                            Cancel
                        </button>
                        <button style={styles.confirmButton} onClick={handleSubmit}>
                            Confirm Order
                        </button>
                    </div>
                </div>
            )}

            {/* Submit Button */}
            {!showConfirm && (
                <button
                    style={{
                        ...styles.submitButton,
                        ...(side === "BUY" ? styles.submitBuy : styles.submitSell),
                        ...(loading ? styles.submitDisabled : {})
                    }}
                    onClick={handleSubmit}
                    disabled={loading}
                >
                    {loading ? "Placing..." : `${side} ${qty} Lots`}
                </button>
            )}

            {/* Mode Indicator */}
            <div style={styles.modeIndicator}>
                {mode === "paper" ? "📄 Paper Trading Mode" : "🔴 LIVE Trading Mode"}
            </div>
        </div>
    )
}

const styles: Record<string, React.CSSProperties> = {
    container: {
        display: "flex",
        flexDirection: "column",
        gap: 12,
        padding: 16,
        height: "100%",
        overflowY: "auto"
    },

    header: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 8
    },

    title: {
        margin: 0,
        fontSize: 16,
        fontWeight: 600,
        color: spaceTheme.textPrimary,
        letterSpacing: "0.04em"
    },

    modeToggle: {
        display: "flex",
        gap: 4,
        background: "rgba(0,0,0,0.3)",
        borderRadius: 8,
        padding: 3
    },

    modeButton: {
        padding: "6px 12px",
        fontSize: 11,
        fontWeight: 600,
        border: "none",
        borderRadius: 6,
        background: "transparent",
        color: spaceTheme.textMuted,
        cursor: "pointer"
    },

    modeButtonActive: {
        padding: "6px 12px",
        fontSize: 11,
        fontWeight: 600,
        border: "none",
        borderRadius: 6,
        background: "rgba(125, 255, 217, 0.2)",
        color: spaceTheme.positive,
        cursor: "pointer"
    },

    modeButtonLive: {
        padding: "6px 12px",
        fontSize: 11,
        fontWeight: 600,
        border: "none",
        borderRadius: 6,
        background: "rgba(255, 100, 100, 0.3)",
        color: "#ff6b6b",
        cursor: "pointer"
    },

    ipWarning: {
        padding: "8px 12px",
        background: "rgba(255, 180, 100, 0.15)",
        border: "1px solid rgba(255, 180, 100, 0.3)",
        borderRadius: 8,
        fontSize: 11,
        color: spaceTheme.warning
    },

    formGroup: {
        display: "flex",
        flexDirection: "column",
        gap: 6
    },

    label: {
        fontSize: 11,
        fontWeight: 600,
        color: spaceTheme.textSecondary,
        textTransform: "uppercase",
        letterSpacing: "0.06em"
    },

    input: {
        padding: "10px 12px",
        fontSize: 14,
        fontWeight: 500,
        background: "rgba(0, 0, 0, 0.4)",
        border: "1px solid rgba(150, 180, 220, 0.2)",
        borderRadius: 8,
        color: spaceTheme.textPrimary,
        outline: "none"
    },

    sideToggle: {
        display: "flex",
        gap: 4,
        background: "rgba(0,0,0,0.3)",
        borderRadius: 8,
        padding: 3
    },

    sideButton: {
        flex: 1,
        padding: "10px 16px",
        fontSize: 13,
        fontWeight: 700,
        border: "none",
        borderRadius: 6,
        background: "rgba(255,255,255,0.05)",
        color: spaceTheme.textMuted,
        cursor: "pointer"
    },

    buyButtonActive: {
        flex: 1,
        padding: "10px 16px",
        fontSize: 13,
        fontWeight: 700,
        border: "none",
        borderRadius: 6,
        background: "linear-gradient(135deg, rgba(0, 200, 150, 0.4) 0%, rgba(0, 150, 100, 0.5) 100%)",
        color: spaceTheme.positive,
        cursor: "pointer",
        boxShadow: "0 2px 12px rgba(0, 200, 150, 0.3)"
    },

    sellButtonActive: {
        flex: 1,
        padding: "10px 16px",
        fontSize: 13,
        fontWeight: 700,
        border: "none",
        borderRadius: 6,
        background: "linear-gradient(135deg, rgba(255, 100, 100, 0.4) 0%, rgba(200, 60, 80, 0.5) 100%)",
        color: spaceTheme.negative,
        cursor: "pointer",
        boxShadow: "0 2px 12px rgba(255, 100, 100, 0.3)"
    },

    typeButtonActive: {
        flex: 1,
        padding: "10px 16px",
        fontSize: 13,
        fontWeight: 700,
        border: "none",
        borderRadius: 6,
        background: "rgba(130, 234, 255, 0.2)",
        color: spaceTheme.accent,
        cursor: "pointer"
    },

    qtyPresets: {
        display: "flex",
        gap: 4,
        marginTop: 4
    },

    qtyPreset: {
        padding: "4px 10px",
        fontSize: 11,
        fontWeight: 600,
        border: "1px solid rgba(150, 180, 220, 0.2)",
        borderRadius: 4,
        background: "transparent",
        color: spaceTheme.textMuted,
        cursor: "pointer"
    },

    error: {
        padding: "10px 12px",
        background: "rgba(255, 100, 100, 0.15)",
        border: "1px solid rgba(255, 100, 100, 0.3)",
        borderRadius: 8,
        fontSize: 12,
        color: spaceTheme.negative
    },

    success: {
        padding: "10px 12px",
        background: "rgba(125, 255, 217, 0.15)",
        border: "1px solid rgba(125, 255, 217, 0.3)",
        borderRadius: 8,
        fontSize: 12,
        color: spaceTheme.positive
    },

    confirmBox: {
        padding: 16,
        background: "rgba(255, 100, 100, 0.1)",
        border: "2px solid rgba(255, 100, 100, 0.4)",
        borderRadius: 12,
        marginTop: 8
    },

    confirmText: {
        margin: 0,
        fontSize: 13,
        color: spaceTheme.textPrimary,
        lineHeight: 1.5
    },

    confirmButtons: {
        display: "flex",
        gap: 8,
        marginTop: 12
    },

    cancelButton: {
        flex: 1,
        padding: "10px 16px",
        fontSize: 13,
        fontWeight: 600,
        border: "1px solid rgba(150, 180, 220, 0.3)",
        borderRadius: 8,
        background: "transparent",
        color: spaceTheme.textMuted,
        cursor: "pointer"
    },

    confirmButton: {
        flex: 1,
        padding: "10px 16px",
        fontSize: 13,
        fontWeight: 700,
        border: "none",
        borderRadius: 8,
        background: "linear-gradient(135deg, #ff4444 0%, #cc2222 100%)",
        color: "#fff",
        cursor: "pointer"
    },

    submitButton: {
        padding: "14px 20px",
        fontSize: 15,
        fontWeight: 700,
        border: "none",
        borderRadius: 10,
        cursor: "pointer",
        letterSpacing: "0.04em",
        marginTop: 8,
        transition: "all 0.2s ease"
    },

    submitBuy: {
        background: "linear-gradient(135deg, #00c896 0%, #008866 100%)",
        color: "#fff",
        boxShadow: "0 4px 20px rgba(0, 200, 150, 0.4)"
    },

    submitSell: {
        background: "linear-gradient(135deg, #ff5555 0%, #cc3344 100%)",
        color: "#fff",
        boxShadow: "0 4px 20px rgba(255, 100, 100, 0.4)"
    },

    submitDisabled: {
        opacity: 0.6,
        cursor: "not-allowed"
    },

    modeIndicator: {
        textAlign: "center",
        fontSize: 11,
        color: spaceTheme.textDim,
        marginTop: 8,
        padding: "6px 0",
        borderTop: "1px solid rgba(150, 180, 220, 0.1)"
    }
}

export default OrderPanel
