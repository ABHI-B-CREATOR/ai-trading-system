import React, { ReactElement, useState } from "react"
import { innerShell, spaceTheme } from "./theme"

interface SignalData {
    strategy?: string
    direction?: string
    action?: string
    confidence?: number
    accuracy?: number
    entry_price?: number
    target?: number
    stoploss?: number
    symbol?: string
    greeks?: {
        delta?: number
        iv?: number
    }
    contributing_strategies?: string[]
    onTakeTrade?: (signal: TradeSignal) => void
}

export interface TradeSignal {
    symbol: string
    action: string
    entry: number
    target: number
    stoploss: number
    qty: number
    riskAmount: number
}

const formatPrice = (value: number | undefined): string => {
    if (value === undefined || value === null || !Number.isFinite(value)) {
        return "--"
    }
    return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`
}

// Calculate suggested quantity based on risk amount
const calculateSuggestedQty = (entry: number, stoploss: number, riskAmount: number): number => {
    const riskPerUnit = Math.abs(entry - stoploss)
    if (riskPerUnit <= 0) return 15 // Default lot size
    const qty = Math.floor(riskAmount / riskPerUnit)
    // Round to lot size multiples (15 for BANKNIFTY, 50 for NIFTY)
    return Math.max(15, Math.floor(qty / 15) * 15)
}

const AISignalPanel = ({ data }: { data: SignalData }): ReactElement => {

    const [riskAmount, setRiskAmount] = useState(5000) // Default risk per trade: ₹5000
    
    const strategy = data?.strategy || "Unified AI"
    const action = data?.direction || data?.action || "HOLD"
    const confidence = data?.confidence || 0
    const accuracy = data?.accuracy || 0
    const entry = data?.entry_price
    const target = data?.target
    const stoploss = data?.stoploss
    const symbol = data?.symbol || "BANKNIFTY"
    const greeks = data?.greeks
    const strategies = data?.contributing_strategies || []

    const isStrong = confidence >= 70
    const isEntryReady = isStrong && accuracy >= 60 && action !== "HOLD" && entry && target && stoploss
    const color =
        action === "BUY"
            ? spaceTheme.positive
            : action === "SELL"
                ? spaceTheme.negative
                : spaceTheme.warning

    // Calculate potential gain/loss
    let potentialGain = 0
    let potentialLoss = 0
    let riskRewardRatio = 0
    if (entry && target && stoploss) {
        if (action === "BUY") {
            potentialGain = ((target - entry) / entry) * 100
            potentialLoss = ((entry - stoploss) / entry) * 100
        } else if (action === "SELL") {
            potentialGain = ((entry - target) / entry) * 100
            potentialLoss = ((stoploss - entry) / entry) * 100
        }
        if (potentialLoss > 0) {
            riskRewardRatio = potentialGain / potentialLoss
        }
    }
    
    // Calculate suggested quantity
    const suggestedQty = entry && stoploss ? calculateSuggestedQty(entry, stoploss, riskAmount) : 15
    const potentialProfit = entry && target ? suggestedQty * Math.abs(target - entry) : 0
    const maxLoss = entry && stoploss ? suggestedQty * Math.abs(entry - stoploss) : 0
    
    const handleTakeTrade = () => {
        if (data.onTakeTrade && entry && target && stoploss) {
            data.onTakeTrade({
                symbol,
                action,
                entry,
                target,
                stoploss,
                qty: suggestedQty,
                riskAmount: maxLoss
            })
        }
    }

    return (

        <div style={styles.container}>

            <div style={styles.header}>
                <span>AI Trading Signal</span>
                {isStrong && <span style={styles.strongBadge}>🔥 STRONG</span>}
            </div>

            <div style={styles.card}>

                {/* Main Signal */}
                <div style={styles.signalRow}>
                    <div style={styles.symbolInfo}>
                        <span style={styles.symbol}>{symbol}</span>
                        <span style={styles.strategyName}>{strategy}</span>
                    </div>
                    <span style={{ 
                        ...styles.action, 
                        background: color,
                        boxShadow: isStrong ? `0 0 20px ${color}40` : undefined
                    }}>
                        {action}
                    </span>
                </div>

                {/* Confidence & Accuracy */}
                <div style={styles.metricsRow}>
                    <div style={styles.metric}>
                        <span style={styles.metricLabel}>Confidence</span>
                        <div style={styles.progressBar}>
                            <div style={{ 
                                ...styles.progressFill, 
                                width: `${confidence}%`,
                                background: confidence >= 70 ? spaceTheme.positive : confidence >= 50 ? spaceTheme.warning : spaceTheme.negative
                            }} />
                        </div>
                        <span style={styles.metricValue}>{confidence}%</span>
                    </div>
                    <div style={styles.metric}>
                        <span style={styles.metricLabel}>Accuracy</span>
                        <div style={styles.progressBar}>
                            <div style={{ 
                                ...styles.progressFill, 
                                width: `${accuracy}%`,
                                background: accuracy >= 60 ? spaceTheme.positive : spaceTheme.warning
                            }} />
                        </div>
                        <span style={styles.metricValue}>{accuracy}%</span>
                    </div>
                </div>

                {/* Price Levels */}
                {(entry || target || stoploss) && (
                    <div style={styles.priceSection}>
                        <div style={styles.priceRow}>
                            <span style={styles.priceLabel}>💰 Entry</span>
                            <span style={styles.priceValue}>{formatPrice(entry)}</span>
                        </div>
                        <div style={styles.priceRow}>
                            <span style={styles.priceLabel}>🎯 Target</span>
                            <span style={{ ...styles.priceValue, color: spaceTheme.positive }}>
                                {formatPrice(target)}
                                {potentialGain > 0 && <span style={styles.percentHint}> (+{potentialGain.toFixed(1)}%)</span>}
                            </span>
                        </div>
                        <div style={styles.priceRow}>
                            <span style={styles.priceLabel}>🛑 Stoploss</span>
                            <span style={{ ...styles.priceValue, color: spaceTheme.negative }}>
                                {formatPrice(stoploss)}
                                {potentialLoss > 0 && <span style={styles.percentHint}> (-{potentialLoss.toFixed(1)}%)</span>}
                            </span>
                        </div>
                    </div>
                )}
                
                {/* Entry Alert Section - Shows when signal is strong enough to trade */}
                {isEntryReady && (
                    <div style={styles.entryAlertSection}>
                        <div style={styles.entryAlertHeader}>
                            <span style={styles.entryAlertIcon}>🚀</span>
                            <span style={styles.entryAlertTitle}>ENTRY ALERT</span>
                            <span style={styles.rrBadge}>RR {riskRewardRatio.toFixed(1)}:1</span>
                        </div>
                        
                        <div style={styles.entryDetails}>
                            <div style={styles.entryRow}>
                                <span>Risk Amount:</span>
                                <select 
                                    value={riskAmount} 
                                    onChange={(e) => setRiskAmount(Number(e.target.value))}
                                    style={styles.riskSelect}
                                >
                                    <option value={2000}>₹2,000</option>
                                    <option value={5000}>₹5,000</option>
                                    <option value={10000}>₹10,000</option>
                                    <option value={15000}>₹15,000</option>
                                    <option value={25000}>₹25,000</option>
                                </select>
                            </div>
                            <div style={styles.entryRow}>
                                <span>Suggested Qty:</span>
                                <span style={styles.qtyValue}>{suggestedQty} units</span>
                            </div>
                            <div style={styles.entryRow}>
                                <span>Potential Profit:</span>
                                <span style={{ color: spaceTheme.positive, fontWeight: 600 }}>
                                    +₹{potentialProfit.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                                </span>
                            </div>
                            <div style={styles.entryRow}>
                                <span>Max Loss:</span>
                                <span style={{ color: spaceTheme.negative, fontWeight: 600 }}>
                                    -₹{maxLoss.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                                </span>
                            </div>
                        </div>
                        
                        <button 
                            style={{
                                ...styles.takeTradeButton,
                                background: action === "BUY" 
                                    ? `linear-gradient(135deg, ${spaceTheme.positive}, #1a7a5e)` 
                                    : `linear-gradient(135deg, ${spaceTheme.negative}, #a83232)`
                            }}
                            onClick={handleTakeTrade}
                        >
                            {action === "BUY" ? "📈" : "📉"} TAKE {action} TRADE
                        </button>
                        
                        <div style={styles.entryNote}>
                            ⚡ High confidence signal • Click to open Order Panel
                        </div>
                    </div>
                )}
                
                {/* Not ready message */}
                {!isEntryReady && action !== "HOLD" && (
                    <div style={styles.waitingSection}>
                        <span style={styles.waitingIcon}>⏳</span>
                        <span style={styles.waitingText}>
                            {confidence < 70 ? "Confidence too low" : 
                             accuracy < 60 ? "Accuracy below threshold" : 
                             "Waiting for complete signal..."}
                        </span>
                    </div>
                )}

                {/* Greeks Summary */}
                {greeks && (greeks.delta !== undefined || greeks.iv !== undefined) && (
                    <div style={styles.greeksSummary}>
                        {greeks.delta !== undefined && (
                            <span>Δ {greeks.delta.toFixed(3)}</span>
                        )}
                        {greeks.iv !== undefined && (
                            <span>IV {greeks.iv.toFixed(1)}%</span>
                        )}
                    </div>
                )}

                {/* Contributing Strategies */}
                {strategies.length > 0 && (
                    <div style={styles.strategiesRow}>
                        {strategies.slice(0, 3).map((s, i) => (
                            <span key={i} style={styles.strategyTag}>{s}</span>
                        ))}
                        {strategies.length > 3 && (
                            <span style={styles.strategyTag}>+{strategies.length - 3}</span>
                        )}
                    </div>
                )}

            </div>

        </div>
    )
}

export default AISignalPanel


// ===== STYLES =====

const styles: any = {

    container: {
        height: "100%",
        background: "linear-gradient(180deg, rgba(5, 10, 20, 0.55) 0%, rgba(2, 5, 12, 0.65) 100%)",
        backdropFilter: "blur(12px)",
        padding: 14,
        borderRadius: 16,
        display: "flex",
        flexDirection: "column",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), 0 0 30px rgba(100,140,200,0.05)",
        border: "1px solid rgba(150, 180, 220, 0.15)",
        minHeight: 0,
        overflow: "hidden"
    },

    header: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        fontSize: 18,
        fontWeight: 700,
        marginBottom: 12,
        color: spaceTheme.textSecondary,
        fontFamily: spaceTheme.titleFamily,
        letterSpacing: "0.03em"
    },

    strongBadge: {
        fontSize: 11,
        padding: "4px 10px",
        background: "linear-gradient(90deg, rgba(255, 180, 50, 0.3), rgba(255, 100, 50, 0.3))",
        borderRadius: 999,
        color: "#FFB040"
    },

    card: {
        ...innerShell,
        borderRadius: 14,
        padding: 14,
        display: "flex",
        flexDirection: "column",
        gap: 14,
        flex: 1
    },

    signalRow: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center"
    },

    symbolInfo: {
        display: "flex",
        flexDirection: "column",
        gap: 2
    },

    symbol: {
        fontSize: 20,
        fontWeight: 700,
        color: spaceTheme.textPrimary
    },

    strategyName: {
        fontSize: 11,
        color: spaceTheme.textMuted
    },

    action: {
        padding: "8px 18px",
        borderRadius: 999,
        fontSize: 14,
        fontWeight: 700,
        color: "#041019",
        boxShadow: "0 0 14px rgba(255,255,255,0.05)"
    },

    metricsRow: {
        display: "flex",
        gap: 12
    },

    metric: {
        flex: 1,
        display: "flex",
        flexDirection: "column",
        gap: 4
    },

    metricLabel: {
        fontSize: 11,
        color: spaceTheme.textMuted,
        textTransform: "uppercase"
    },

    progressBar: {
        height: 6,
        background: "rgba(255,255,255,0.08)",
        borderRadius: 999,
        overflow: "hidden"
    },

    progressFill: {
        height: "100%",
        borderRadius: 999,
        transition: "width 0.3s ease"
    },

    metricValue: {
        fontSize: 14,
        fontWeight: 600,
        color: spaceTheme.textPrimary
    },

    priceSection: {
        display: "flex",
        flexDirection: "column",
        gap: 8,
        padding: "10px 0",
        borderTop: "1px solid rgba(255,255,255,0.06)",
        borderBottom: "1px solid rgba(255,255,255,0.06)"
    },

    priceRow: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center"
    },

    priceLabel: {
        fontSize: 13,
        color: spaceTheme.textMuted
    },

    priceValue: {
        fontSize: 15,
        fontWeight: 600,
        color: spaceTheme.textPrimary,
        fontFamily: "monospace"
    },

    percentHint: {
        fontSize: 11,
        fontWeight: 400
    },

    greeksSummary: {
        display: "flex",
        gap: 12,
        fontSize: 12,
        color: spaceTheme.textDim,
        fontFamily: "monospace"
    },

    strategiesRow: {
        display: "flex",
        gap: 6,
        flexWrap: "wrap"
    },

    strategyTag: {
        fontSize: 10,
        padding: "3px 8px",
        background: "rgba(114, 255, 210, 0.1)",
        borderRadius: 999,
        color: spaceTheme.textMuted
    },
    
    // Entry Alert Section Styles
    entryAlertSection: {
        background: "linear-gradient(135deg, rgba(72, 255, 167, 0.08) 0%, rgba(50, 180, 120, 0.05) 100%)",
        border: "1px solid rgba(72, 255, 167, 0.25)",
        borderRadius: 12,
        padding: 14,
        marginTop: 4
    },
    
    entryAlertHeader: {
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: 12
    },
    
    entryAlertIcon: {
        fontSize: 18
    },
    
    entryAlertTitle: {
        fontSize: 13,
        fontWeight: 700,
        color: "#48ffa7",
        letterSpacing: "0.08em",
        flex: 1
    },
    
    rrBadge: {
        fontSize: 10,
        padding: "3px 8px",
        background: "rgba(255, 200, 50, 0.2)",
        border: "1px solid rgba(255, 200, 50, 0.3)",
        borderRadius: 999,
        color: "#ffc832",
        fontWeight: 600
    },
    
    entryDetails: {
        display: "flex",
        flexDirection: "column",
        gap: 8,
        marginBottom: 12
    },
    
    entryRow: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        fontSize: 12,
        color: spaceTheme.textMuted
    },
    
    riskSelect: {
        background: "rgba(30, 40, 60, 0.8)",
        border: "1px solid rgba(100, 140, 200, 0.2)",
        borderRadius: 6,
        padding: "4px 8px",
        color: spaceTheme.textPrimary,
        fontSize: 12,
        cursor: "pointer",
        outline: "none"
    },
    
    qtyValue: {
        fontWeight: 700,
        color: spaceTheme.accent,
        fontSize: 13
    },
    
    takeTradeButton: {
        width: "100%",
        padding: "12px 16px",
        border: "none",
        borderRadius: 8,
        fontSize: 13,
        fontWeight: 700,
        color: "#fff",
        cursor: "pointer",
        letterSpacing: "0.05em",
        transition: "all 0.2s ease",
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)"
    },
    
    entryNote: {
        fontSize: 10,
        color: spaceTheme.textDim,
        textAlign: "center",
        marginTop: 10,
        opacity: 0.7
    },
    
    waitingSection: {
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        padding: 12,
        background: "rgba(255, 200, 50, 0.05)",
        border: "1px dashed rgba(255, 200, 50, 0.2)",
        borderRadius: 8,
        marginTop: 4
    },
    
    waitingIcon: {
        fontSize: 14
    },
    
    waitingText: {
        fontSize: 11,
        color: spaceTheme.warning,
        fontStyle: "italic"
    }

}
