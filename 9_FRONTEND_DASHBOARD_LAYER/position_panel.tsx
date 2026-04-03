/**
 * Position Panel - Displays open positions with P&L and square-off functionality
 */

import React, { useState, useEffect, useCallback } from "react"
import { spaceTheme } from "./theme"
import { getBackendBaseUrl } from "./api_service"

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
    order_id?: string
    timestamp?: string
}

type PositionPanelProps = {
    onSquareOff?: (position: Position) => void
    refreshTrigger?: number
}

const PositionPanel: React.FC<PositionPanelProps> = ({ onSquareOff, refreshTrigger }) => {
    const [positions, setPositions] = useState<Position[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [squaringOff, setSquaringOff] = useState<string | null>(null)

    const fetchPositions = useCallback(async () => {
        try {
            const response = await fetch(`${getBackendBaseUrl()}/api/order/positions`)
            if (!response.ok) throw new Error("Failed to fetch positions")
            
            const data = await response.json()
            setPositions(data.positions || [])
            setError(null)
        } catch (e: any) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }, [])

    // Initial fetch and polling
    useEffect(() => {
        fetchPositions()
        const interval = setInterval(fetchPositions, 2000) // Poll every 2 seconds
        return () => clearInterval(interval)
    }, [fetchPositions])

    // Refetch when trigger changes
    useEffect(() => {
        if (refreshTrigger) {
            fetchPositions()
        }
    }, [refreshTrigger, fetchPositions])

    const handleSquareOff = async (position: Position) => {
        setSquaringOff(position.position_id)
        
        try {
            const response = await fetch(`${getBackendBaseUrl()}/api/order/square_off`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    position_id: position.position_id,
                    mode: position.mode
                })
            })

            const data = await response.json()

            if (response.ok && data.status === "SQUARED_OFF") {
                // Refresh positions
                fetchPositions()
                onSquareOff?.(position)
            } else {
                setError(data.message || "Square-off failed")
            }
        } catch (e: any) {
            setError(e.message)
        } finally {
            setSquaringOff(null)
        }
    }

    const totalPnl = positions.reduce((sum, pos) => sum + (pos.pnl || 0), 0)

    return (
        <div style={styles.container}>
            {/* Header */}
            <div style={styles.header}>
                <h3 style={styles.title}>📊 Positions</h3>
                <div style={{
                    ...styles.totalPnl,
                    color: totalPnl >= 0 ? spaceTheme.positive : spaceTheme.negative
                }}>
                    {totalPnl >= 0 ? "+" : ""}₹{totalPnl.toFixed(2)}
                </div>
            </div>

            {/* Content */}
            {loading ? (
                <div style={styles.loading}>Loading positions...</div>
            ) : error ? (
                <div style={styles.error}>{error}</div>
            ) : positions.length === 0 ? (
                <div style={styles.empty}>No open positions</div>
            ) : (
                <div style={styles.positionList}>
                    {positions.map((pos) => (
                        <div key={pos.position_id} style={styles.positionCard}>
                            {/* Symbol & Side */}
                            <div style={styles.positionHeader}>
                                <div style={styles.symbolInfo}>
                                    <span style={{
                                        ...styles.sideBadge,
                                        background: pos.side === "BUY" 
                                            ? "rgba(0, 200, 150, 0.2)" 
                                            : "rgba(255, 100, 100, 0.2)",
                                        color: pos.side === "BUY" 
                                            ? spaceTheme.positive 
                                            : spaceTheme.negative
                                    }}>
                                        {pos.side}
                                    </span>
                                    <span style={styles.symbol}>{pos.symbol}</span>
                                </div>
                                <span style={{
                                    ...styles.modeBadge,
                                    background: pos.mode === "paper" 
                                        ? "rgba(130, 234, 255, 0.15)" 
                                        : "rgba(255, 100, 100, 0.15)"
                                }}>
                                    {pos.mode === "paper" ? "📄" : "🔴"}
                                </span>
                            </div>

                            {/* Qty & Prices */}
                            <div style={styles.priceRow}>
                                <div style={styles.priceItem}>
                                    <span style={styles.priceLabel}>Qty</span>
                                    <span style={styles.priceValue}>{pos.qty}</span>
                                </div>
                                <div style={styles.priceItem}>
                                    <span style={styles.priceLabel}>Avg</span>
                                    <span style={styles.priceValue}>₹{pos.avg_price.toFixed(2)}</span>
                                </div>
                                <div style={styles.priceItem}>
                                    <span style={styles.priceLabel}>LTP</span>
                                    <span style={styles.priceValue}>₹{(pos.ltp || pos.avg_price).toFixed(2)}</span>
                                </div>
                            </div>

                            {/* P&L */}
                            <div style={styles.pnlRow}>
                                <div style={{
                                    ...styles.pnl,
                                    color: (pos.pnl || 0) >= 0 ? spaceTheme.positive : spaceTheme.negative
                                }}>
                                    {(pos.pnl || 0) >= 0 ? "+" : ""}₹{(pos.pnl || 0).toFixed(2)}
                                    <span style={styles.pnlPct}>
                                        ({(pos.pnl_pct || 0) >= 0 ? "+" : ""}{(pos.pnl_pct || 0).toFixed(2)}%)
                                    </span>
                                </div>
                            </div>

                            {/* SL/Target */}
                            {(pos.stoploss || pos.target) && (
                                <div style={styles.slTpRow}>
                                    {pos.stoploss && (
                                        <span style={styles.slLabel}>
                                            SL: ₹{pos.stoploss.toFixed(2)}
                                        </span>
                                    )}
                                    {pos.target && (
                                        <span style={styles.tpLabel}>
                                            TP: ₹{pos.target.toFixed(2)}
                                        </span>
                                    )}
                                </div>
                            )}

                            {/* Square-off Button */}
                            <button
                                style={{
                                    ...styles.squareOffButton,
                                    ...(squaringOff === pos.position_id ? styles.squareOffDisabled : {})
                                }}
                                onClick={() => handleSquareOff(pos)}
                                disabled={squaringOff === pos.position_id}
                            >
                                {squaringOff === pos.position_id ? "Closing..." : "Square Off"}
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}

const styles: Record<string, React.CSSProperties> = {
    container: {
        display: "flex",
        flexDirection: "column",
        height: "100%",
        gap: 12
    },

    header: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        paddingBottom: 10,
        borderBottom: "1px solid rgba(150, 180, 220, 0.1)"
    },

    title: {
        margin: 0,
        fontSize: 15,
        fontWeight: 600,
        color: spaceTheme.textPrimary,
        letterSpacing: "0.04em"
    },

    totalPnl: {
        fontSize: 16,
        fontWeight: 700,
        fontFamily: "monospace"
    },

    loading: {
        padding: 20,
        textAlign: "center",
        color: spaceTheme.textMuted,
        fontSize: 13
    },

    error: {
        padding: "10px 12px",
        background: "rgba(255, 100, 100, 0.15)",
        border: "1px solid rgba(255, 100, 100, 0.3)",
        borderRadius: 8,
        fontSize: 12,
        color: spaceTheme.negative
    },

    empty: {
        padding: 30,
        textAlign: "center",
        color: spaceTheme.textDim,
        fontSize: 13
    },

    positionList: {
        display: "flex",
        flexDirection: "column",
        gap: 10,
        overflowY: "auto",
        flex: 1
    },

    positionCard: {
        padding: 12,
        background: "rgba(0, 0, 0, 0.3)",
        border: "1px solid rgba(150, 180, 220, 0.12)",
        borderRadius: 10,
        display: "flex",
        flexDirection: "column",
        gap: 8
    },

    positionHeader: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center"
    },

    symbolInfo: {
        display: "flex",
        alignItems: "center",
        gap: 8
    },

    sideBadge: {
        padding: "3px 8px",
        fontSize: 10,
        fontWeight: 700,
        borderRadius: 4,
        letterSpacing: "0.05em"
    },

    symbol: {
        fontSize: 13,
        fontWeight: 600,
        color: spaceTheme.textPrimary,
        letterSpacing: "0.02em"
    },

    modeBadge: {
        padding: "3px 6px",
        borderRadius: 4,
        fontSize: 10
    },

    priceRow: {
        display: "flex",
        justifyContent: "space-between",
        gap: 12
    },

    priceItem: {
        display: "flex",
        flexDirection: "column",
        gap: 2
    },

    priceLabel: {
        fontSize: 10,
        color: spaceTheme.textDim,
        textTransform: "uppercase",
        letterSpacing: "0.05em"
    },

    priceValue: {
        fontSize: 12,
        fontWeight: 600,
        color: spaceTheme.textSecondary,
        fontFamily: "monospace"
    },

    pnlRow: {
        display: "flex",
        justifyContent: "flex-end"
    },

    pnl: {
        fontSize: 14,
        fontWeight: 700,
        fontFamily: "monospace"
    },

    pnlPct: {
        fontSize: 11,
        marginLeft: 6,
        opacity: 0.8
    },

    slTpRow: {
        display: "flex",
        gap: 12,
        fontSize: 11
    },

    slLabel: {
        color: spaceTheme.negative,
        fontFamily: "monospace"
    },

    tpLabel: {
        color: spaceTheme.positive,
        fontFamily: "monospace"
    },

    squareOffButton: {
        padding: "8px 14px",
        fontSize: 12,
        fontWeight: 600,
        border: "1px solid rgba(255, 100, 100, 0.4)",
        borderRadius: 6,
        background: "rgba(255, 100, 100, 0.1)",
        color: spaceTheme.negative,
        cursor: "pointer",
        marginTop: 4,
        transition: "all 0.2s ease"
    },

    squareOffDisabled: {
        opacity: 0.5,
        cursor: "not-allowed"
    }
}

export default PositionPanel
