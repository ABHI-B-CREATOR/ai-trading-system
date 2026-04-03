import React, { ReactElement } from "react"
import { innerShell, spaceTheme } from "./theme"

interface GreeksData {
    delta?: number
    gamma?: number
    theta?: number
    vega?: number
    iv?: number
    iv_percentile?: number
    atm_iv?: number
    symbol?: string
}

const formatGreek = (value: number | undefined, decimals: number = 4): string => {
    if (value === undefined || value === null || !Number.isFinite(value)) {
        return "--"
    }
    return value.toFixed(decimals)
}

const formatPercent = (value: number | undefined): string => {
    if (value === undefined || value === null || !Number.isFinite(value)) {
        return "--"
    }
    return `${value.toFixed(1)}%`
}

const getGreekColor = (greek: string, value: number | undefined): string => {
    if (value === undefined || value === null) return spaceTheme.textMuted

    switch (greek) {
        case "delta":
            if (value > 0.6) return spaceTheme.positive
            if (value < -0.6) return spaceTheme.negative
            return spaceTheme.textPrimary
        case "gamma":
            if (value > 0.01) return spaceTheme.warning
            return spaceTheme.textPrimary
        case "theta":
            return value < 0 ? spaceTheme.negative : spaceTheme.positive
        case "vega":
            if (value > 50) return spaceTheme.warning
            return spaceTheme.textPrimary
        case "iv":
            if (value > 25) return spaceTheme.warning
            if (value > 35) return spaceTheme.negative
            return spaceTheme.positive
        default:
            return spaceTheme.textPrimary
    }
}

const GreeksPanel = ({ data }: { data: GreeksData }): ReactElement => {
    const delta = data?.delta
    const gamma = data?.gamma
    const theta = data?.theta
    const vega = data?.vega
    const iv = data?.iv || data?.atm_iv
    const ivPercentile = data?.iv_percentile
    const symbol = data?.symbol || "BANKNIFTY"

    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <span>Greeks Analysis</span>
                <span style={styles.symbol}>{symbol}</span>
            </div>

            <div style={styles.greeksGrid}>
                {/* Delta */}
                <div style={styles.greekCard}>
                    <div style={styles.greekLabel}>Delta (Δ)</div>
                    <div style={{ ...styles.greekValue, color: getGreekColor("delta", delta) }}>
                        {formatGreek(delta, 3)}
                    </div>
                    <div style={styles.greekHint}>
                        {delta !== undefined && delta > 0.5 ? "Bullish" : delta !== undefined && delta < -0.5 ? "Bearish" : "Neutral"}
                    </div>
                </div>

                {/* Gamma */}
                <div style={styles.greekCard}>
                    <div style={styles.greekLabel}>Gamma (Γ)</div>
                    <div style={{ ...styles.greekValue, color: getGreekColor("gamma", gamma) }}>
                        {formatGreek(gamma, 4)}
                    </div>
                    <div style={styles.greekHint}>
                        {gamma !== undefined && gamma > 0.01 ? "High Sensitivity" : "Normal"}
                    </div>
                </div>

                {/* Theta */}
                <div style={styles.greekCard}>
                    <div style={styles.greekLabel}>Theta (Θ)</div>
                    <div style={{ ...styles.greekValue, color: getGreekColor("theta", theta) }}>
                        {formatGreek(theta, 2)}
                    </div>
                    <div style={styles.greekHint}>
                        {theta !== undefined ? `₹${Math.abs(theta).toFixed(0)}/day decay` : "--"}
                    </div>
                </div>

                {/* Vega */}
                <div style={styles.greekCard}>
                    <div style={styles.greekLabel}>Vega (ν)</div>
                    <div style={{ ...styles.greekValue, color: getGreekColor("vega", vega) }}>
                        {formatGreek(vega, 2)}
                    </div>
                    <div style={styles.greekHint}>
                        {vega !== undefined && vega > 50 ? "Vol Sensitive" : "Normal"}
                    </div>
                </div>
            </div>

            {/* IV Section */}
            <div style={styles.ivSection}>
                <div style={styles.ivRow}>
                    <span style={styles.ivLabel}>Implied Volatility</span>
                    <span style={{ ...styles.ivValue, color: getGreekColor("iv", iv) }}>
                        {formatPercent(iv)}
                    </span>
                </div>
                {ivPercentile !== undefined && (
                    <div style={styles.ivRow}>
                        <span style={styles.ivLabel}>IV Percentile</span>
                        <span style={styles.ivValue}>{formatPercent(ivPercentile)}</span>
                    </div>
                )}
                <div style={styles.ivBar}>
                    <div 
                        style={{ 
                            ...styles.ivFill, 
                            width: `${Math.min(iv || 0, 50) * 2}%`,
                            background: iv && iv > 25 
                                ? `linear-gradient(90deg, ${spaceTheme.warning}, ${spaceTheme.negative})`
                                : `linear-gradient(90deg, ${spaceTheme.positive}, ${spaceTheme.warning})`
                        }} 
                    />
                </div>
                <div style={styles.ivHint}>
                    {iv !== undefined && iv > 30 
                        ? "🔥 High IV - Consider selling options" 
                        : iv !== undefined && iv < 15 
                        ? "📉 Low IV - Consider buying options"
                        : "Normal IV range"}
                </div>
            </div>
        </div>
    )
}

export default GreeksPanel


const styles: any = {
    container: {
        height: "100%",
        background: "linear-gradient(180deg, rgba(5, 10, 20, 0.55) 0%, rgba(2, 5, 12, 0.65) 100%)",
        backdropFilter: "blur(12px)",
        padding: 16,
        borderRadius: 16,
        display: "flex",
        flexDirection: "column",
        gap: 14,
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
        color: spaceTheme.textSecondary,
        fontFamily: spaceTheme.titleFamily,
        letterSpacing: "0.03em"
    },

    symbol: {
        fontSize: 12,
        padding: "4px 10px",
        background: "rgba(114, 255, 210, 0.12)",
        borderRadius: 999,
        color: spaceTheme.positive
    },

    greeksGrid: {
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 10
    },

    greekCard: {
        ...innerShell,
        borderRadius: 12,
        padding: 12,
        display: "flex",
        flexDirection: "column",
        gap: 4
    },

    greekLabel: {
        fontSize: 11,
        color: spaceTheme.textMuted,
        textTransform: "uppercase",
        letterSpacing: "0.08em"
    },

    greekValue: {
        fontSize: 22,
        fontWeight: 700,
        fontFamily: "monospace"
    },

    greekHint: {
        fontSize: 10,
        color: spaceTheme.textDim
    },

    ivSection: {
        ...innerShell,
        borderRadius: 12,
        padding: 12,
        display: "flex",
        flexDirection: "column",
        gap: 8
    },

    ivRow: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center"
    },

    ivLabel: {
        fontSize: 13,
        color: spaceTheme.textMuted
    },

    ivValue: {
        fontSize: 18,
        fontWeight: 700,
        fontFamily: "monospace",
        color: spaceTheme.textPrimary
    },

    ivBar: {
        height: 6,
        background: "rgba(255,255,255,0.08)",
        borderRadius: 999,
        overflow: "hidden"
    },

    ivFill: {
        height: "100%",
        borderRadius: 999,
        transition: "width 0.3s ease"
    },

    ivHint: {
        fontSize: 11,
        color: spaceTheme.textDim,
        textAlign: "center" as const
    }
}
