import React, { ReactElement } from "react"
import { innerShell, spaceTheme } from "./theme"

interface AnalyticsData {
    regime?: string
    volatility?: number
    momentum?: number
    symbol?: string
}

const AnalyticsDashboard = ({ data }: { data: AnalyticsData }): ReactElement => {

    const regime = data?.regime || "Neutral"
    const volatility = data?.volatility || 0
    const momentum = data?.momentum || 0
    const symbol = data?.symbol || "NIFTY"

    const volColor =
        volatility > 70 ? spaceTheme.negative :
        volatility > 40 ? spaceTheme.warning :
        spaceTheme.positive

    const momColor =
        momentum > 0 ? spaceTheme.positive :
        momentum < 0 ? spaceTheme.negative :
        spaceTheme.warning

    return (

        <div style={styles.container}>

            <div style={styles.header}>
                <span>Quant Analytics</span>
                <span style={styles.symbol}>{symbol}</span>
            </div>

            <div style={styles.card}>

                <div style={styles.row}>
                    <span>Market Regime</span>
                    <span style={styles.value}>{regime}</span>
                </div>

                <div style={styles.row}>
                    <span>Volatility</span>
                    <span style={{ ...styles.badge, background: volColor }}>
                        {volatility}
                    </span>
                </div>

                <div style={styles.row}>
                    <span>Momentum</span>
                    <span style={{ ...styles.badge, background: momColor }}>
                        {momentum}
                    </span>
                </div>

            </div>

            {/* ===== SIMPLE HEAT BAR ===== */}
            <div style={styles.heatBox}>
                <div
                    style={{
                        height: "100%",
                        width: `${Math.min(volatility, 100)}%`,
                        background: volColor,
                        transition: "0.4s"
                    }}
                />
            </div>

        </div>
    )
}

export default AnalyticsDashboard


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

    symbol: {
        fontSize: 12,
        padding: "4px 10px",
        background: "rgba(114, 255, 210, 0.12)",
        borderRadius: 999,
        color: spaceTheme.positive
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

    row: {
        display: "flex",
        justifyContent: "space-between",
        fontSize: 15,
        color: spaceTheme.textSecondary
    },

    value: {
        fontWeight: 600
    },

    badge: {
        padding: "5px 10px",
        borderRadius: 999,
        fontSize: 13,
        color: "#041019",
        fontWeight: 700,
        boxShadow: "0 0 12px rgba(255,255,255,0.05)"
    },

    heatBox: {
        marginTop: 14,
        height: 14,
        ...innerShell,
        borderRadius: 999,
        overflow: "hidden"
    }

}
