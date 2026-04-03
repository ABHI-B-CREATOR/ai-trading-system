import React, { ReactElement } from "react"
import { innerShell, spaceTheme } from "./theme"

const buildSeries = (equity: number[], pnl: number): number[] => {
    if (equity.length > 1) {
        return equity
    }

    if (!pnl) {
        return []
    }

    return Array.from({ length: 16 }, (_, index) => {
        const progress = (index + 1) / 16
        return pnl * progress
    })
}

const PnlCurveChart = ({ data }: any): ReactElement => {
    const equity = Array.isArray(data?.equity) ? data.equity : []
    const pnl = Number(data?.pnl || 0)
    const trades = Number(data?.trades || 0)
    const winRate = Number(data?.win_rate || 0)
    const series = buildSeries(equity, pnl)

    if (series.length === 0) {
        return (
            <div style={styles.container}>
                <div style={styles.header}>Equity Curve</div>
                <div style={styles.emptyState}>
                    Waiting for executed trades to draw the equity curve.
                </div>
                <div style={styles.footer}>
                    <span>Trades: {Math.round(trades)}</span>
                    <span>Win: {Math.round(winRate)}%</span>
                    <span style={{ color: pnl >= 0 ? spaceTheme.positive : spaceTheme.negative }}>P&L: ₹{Math.round(pnl)}</span>
                </div>
            </div>
        )
    }

    const min = Math.min(...series, 0)
    const max = Math.max(...series, 0, 1)
    const range = max - min || 1

    const points = series.map((value, index) => {
        const x = (index / Math.max(series.length - 1, 1)) * 100
        const y = 100 - ((value - min) / range) * 100
        return `${x},${y}`
    }).join(" ")

    const areaPoints = `0,100 ${points} 100,100`
    const trendColor = pnl >= 0 ? spaceTheme.positive : spaceTheme.negative

    return (
        <div style={styles.container}>
            <div style={styles.header}>Equity Curve</div>

            <div style={styles.chart}>
                <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={styles.svg}>
                    <line x1="0" y1="25" x2="100" y2="25" style={styles.gridLine} />
                    <line x1="0" y1="50" x2="100" y2="50" style={styles.gridLine} />
                    <line x1="0" y1="75" x2="100" y2="75" style={styles.gridLine} />
                    <polygon
                        points={areaPoints}
                        fill={pnl >= 0 ? "rgba(114, 255, 210, 0.08)" : "rgba(255, 128, 151, 0.08)"}
                    />
                    <polyline
                        points={points}
                        fill="none"
                        stroke={trendColor}
                        strokeWidth="1.2"
                        strokeLinejoin="round"
                        strokeLinecap="round"
                    />
                </svg>
            </div>

            <div style={styles.footer}>
                <span>Trades: {Math.round(trades)}</span>
                <span>Win: {Math.round(winRate)}%</span>
                <span style={{ color: trendColor }}>P&L: ₹{Math.round(pnl)}</span>
            </div>
        </div>
    )
}

export default PnlCurveChart


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
        fontSize: 18,
        fontWeight: 700,
        marginBottom: 12,
        color: spaceTheme.textSecondary,
        fontFamily: spaceTheme.titleFamily,
        letterSpacing: "0.03em"
    },

    chart: {
        flex: 1,
        ...innerShell,
        borderRadius: 14,
        padding: 10,
        overflow: "hidden",
        minHeight: 160
    },

    svg: {
        width: "100%",
        height: "100%",
        display: "block"
    },

    gridLine: {
        stroke: "rgba(120, 172, 209, 0.18)",
        strokeWidth: 0.8,
        strokeDasharray: "4 4"
    },

    emptyState: {
        flex: 1,
        ...innerShell,
        borderRadius: 14,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: spaceTheme.textMuted,
        fontSize: 14,
        padding: 18,
        textAlign: "center",
        minHeight: 160
    },

    footer: {
        fontSize: 14,
        color: spaceTheme.textMuted,
        marginTop: 10,
        display: "flex",
        gap: 16,
        flexWrap: "wrap"
    }

}
