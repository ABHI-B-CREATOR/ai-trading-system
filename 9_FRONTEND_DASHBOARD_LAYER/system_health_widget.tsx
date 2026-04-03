import React, { ReactElement } from "react"
import { innerShell, spaceTheme } from "./theme"

const normalizeLabel = (value: any, fallback: string = "Unknown"): string => {
    if (value === undefined || value === null || value === "") {
        return fallback
    }

    return String(value)
        .replace(/_/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

const formatLastTick = (value: any): string => {
    if (!value) {
        return "--"
    }

    const date = new Date(value)
    if (Number.isNaN(date.getTime())) {
        return "--"
    }

    return date.toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    })
}

const getBadgeColors = (value: any): { background: string, color: string } => {
    const normalized = String(value || "unknown").toLowerCase()

    if (["running", "live_connected", "connected", "open", "valid"].includes(normalized)) {
        return {
            background: "rgba(125, 255, 217, 0.94)",
            color: "#041019"
        }
    }

    if (["closed", "pre_open", "unknown"].includes(normalized)) {
        return {
            background: "rgba(217, 222, 241, 0.9)",
            color: "#05111d"
        }
    }

    if (["demo_fallback", "starting", "checking", "connecting", "paper", "live", "demo", "not_required"].includes(normalized)) {
        return {
            background: "rgba(255, 211, 139, 0.94)",
            color: "#1f1205"
        }
    }

    if (["error", "token_expired", "expired", "invalid", "missing", "disconnected", "stopped"].includes(normalized)) {
        return {
            background: "rgba(255, 136, 176, 0.94)",
            color: "#250712"
        }
    }

    return {
        background: "rgba(217, 222, 241, 0.9)",
        color: "#05111d"
    }
}

const badgeStyle = (value: any): any => {
    const colors = getBadgeColors(value)
    return {
        ...styles.badge,
        background: colors.background,
        color: colors.color
    }
}

const SystemHealthWidget = ({ system }: any): ReactElement => {
    const backendStatus = system?.status || "UNKNOWN"
    const tradingMode = system?.mode || system?.trading_mode || "paper"
    const riskMode = system?.risk_mode || "normal"
    const dataMode = system?.data_mode || "unknown"
    const feedStatus = system?.feed_status || "unknown"
    const tokenState = system?.token_state || "unknown"
    const marketState = system?.market_state || "unknown"
    const lastTickTime = system?.last_tick_time || ""
    const lastError = system?.last_error || ""
    const streamClients = system?.stream_clients ?? 0

    return (
        <div style={styles.container}>
            <div style={styles.header}>
                System Health
            </div>

            <div style={styles.card}>
                <div style={styles.row}>
                    <span>Backend</span>
                    <span style={badgeStyle(backendStatus)}>
                        {normalizeLabel(backendStatus)}
                    </span>
                </div>

                <div style={styles.row}>
                    <span>Feed</span>
                    <span style={badgeStyle(feedStatus)}>
                        {normalizeLabel(feedStatus)}
                    </span>
                </div>

                <div style={styles.row}>
                    <span>Market</span>
                    <span style={badgeStyle(marketState)}>
                        {normalizeLabel(marketState)}
                    </span>
                </div>

                <div style={styles.row}>
                    <span>Token</span>
                    <span style={badgeStyle(tokenState)}>
                        {normalizeLabel(tokenState)}
                    </span>
                </div>

                <div style={styles.row}>
                    <span>Data Mode</span>
                    <span style={badgeStyle(dataMode)}>
                        {normalizeLabel(dataMode)}
                    </span>
                </div>

                <div style={styles.row}>
                    <span>Trading Mode</span>
                    <span style={styles.value}>{normalizeLabel(tradingMode)}</span>
                </div>

                <div style={styles.row}>
                    <span>Risk Mode</span>
                    <span style={styles.value}>{normalizeLabel(riskMode)}</span>
                </div>

                <div style={styles.row}>
                    <span>Last Tick</span>
                    <span style={styles.valueSmall}>{formatLastTick(lastTickTime)}</span>
                </div>

                <div style={styles.row}>
                    <span>Clients</span>
                    <span style={styles.value}>{String(streamClients)}</span>
                </div>

                {lastError && (
                    <div style={styles.errorBlock}>
                        {lastError}
                    </div>
                )}
            </div>
        </div>
    )
}

export default SystemHealthWidget


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

    card: {
        ...innerShell,
        borderRadius: 14,
        padding: 14,
        display: "flex",
        flexDirection: "column",
        gap: 12,
        flex: 1
    },

    row: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 10,
        fontSize: 15,
        color: spaceTheme.textSecondary
    },

    badge: {
        padding: "5px 10px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 700,
        boxShadow: "0 0 14px rgba(255,255,255,0.05)",
        letterSpacing: "0.03em",
        flexShrink: 0
    },

    value: {
        fontWeight: 600,
        color: spaceTheme.accentStrong
    },

    valueSmall: {
        fontWeight: 600,
        color: spaceTheme.textPrimary,
        fontSize: 13,
        textAlign: "right"
    },

    errorBlock: {
        marginTop: 2,
        padding: "10px 12px",
        borderRadius: 12,
        background: "rgba(255, 136, 176, 0.12)",
        border: "1px solid rgba(255, 136, 176, 0.22)",
        color: spaceTheme.negative,
        fontSize: 12,
        lineHeight: 1.5
    }
}
