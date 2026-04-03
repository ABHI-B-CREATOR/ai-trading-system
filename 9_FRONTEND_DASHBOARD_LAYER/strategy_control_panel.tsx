import React, { useState, ReactElement } from "react"
import { getBackendBaseUrl } from "./api_service"
import { innerShell, spaceTheme } from "./theme"

const StrategyControlPanel = ({ system }: any): ReactElement => {

    const [loading, setLoading] = useState(false)
    const mode = system?.mode || system?.trading_mode || "paper"
    const dataMode = system?.data_mode || "unknown"

    const callApi = async (endpoint: string, body?: any) => {

        setLoading(true)

        try {
            await fetch(`${getBackendBaseUrl()}${endpoint}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body || {})
            })
        } catch (e) {
            console.error(e)
        }

        setLoading(false)
    }

    return (

        <div style={styles.container}>

            <div style={styles.header}>
                Strategy Control
            </div>

            <div style={styles.section}>

                <button
                    style={styles.btnGreen}
                    onClick={() => callApi("/api/strategy/start", { strategy: "trend" })}
                >
                    Start Trend
                </button>

                <button
                    style={styles.btnRed}
                    onClick={() => callApi("/api/strategy/stop", { strategy: "trend" })}
                >
                    Stop Trend
                </button>

                <button
                    style={styles.btnYellow}
                    onClick={() => callApi("/api/strategy/emergency_pause")}
                >
                    Emergency Pause
                </button>

            </div>

            <div style={styles.statusBox}>
                <div>Status: {system?.status || "UNKNOWN"}</div>
                <div>Mode: {mode}</div>
                <div>Data: {dataMode}</div>
                {loading && <div>Sending command...</div>}
            </div>

        </div>
    )
}

export default StrategyControlPanel


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
        fontSize: 18,
        fontWeight: 700,
        marginBottom: 12,
        color: spaceTheme.textSecondary,
        fontFamily: spaceTheme.titleFamily,
        letterSpacing: "0.03em"
    },

    section: {
        display: "flex",
        flexDirection: "column",
        gap: 12
    },

    btnGreen: {
        background: "linear-gradient(180deg, rgba(114,255,210,0.95) 0%, rgba(59,206,165,0.95) 100%)",
        border: "1px solid rgba(171,255,230,0.24)",
        padding: 14,
        borderRadius: 12,
        cursor: "pointer",
        color: "#031018",
        fontWeight: 700,
        boxShadow: "0 0 18px rgba(114,255,210,0.16)"
    },

    btnRed: {
        background: "linear-gradient(180deg, rgba(255,128,151,0.95) 0%, rgba(220,84,110,0.95) 100%)",
        border: "1px solid rgba(255,180,195,0.2)",
        padding: 14,
        borderRadius: 12,
        cursor: "pointer",
        color: "#1b0710",
        fontWeight: 700,
        boxShadow: "0 0 18px rgba(255,128,151,0.14)"
    },

    btnYellow: {
        background: "linear-gradient(180deg, rgba(255,224,163,0.98) 0%, rgba(255,198,104,0.98) 100%)",
        border: "1px solid rgba(255,233,190,0.2)",
        padding: 14,
        borderRadius: 12,
        cursor: "pointer",
        color: "#24180a",
        fontWeight: 700,
        boxShadow: "0 0 18px rgba(255,210,133,0.14)"
    },

    statusBox: {
        marginTop: "auto",
        ...innerShell,
        padding: 12,
        borderRadius: 12,
        fontSize: 14,
        color: spaceTheme.textMuted
    }

}
