import React, { ReactElement } from "react"
import { innerShell, spaceTheme } from "./theme"

const formatNumber = (value: any): string => {
    const number = typeof value === "number" ? value : Number(value)
    if (!Number.isFinite(number)) {
        return "--"
    }

    return number.toLocaleString("en-IN", {
        maximumFractionDigits: 2
    })
}

const formatInteger = (value: any): string => {
    const number = typeof value === "number" ? value : Number(value)
    if (!Number.isFinite(number)) {
        return "--"
    }

    return Math.round(number).toLocaleString("en-IN")
}

const OptionChainHeatmap = ({ data }: any): ReactElement => {
    const strikes = Array.isArray(data?.strikes) ? data.strikes : []
    const atmStrike = data?.atm_strike
    const expiry = data?.expiry
    const symbol = data?.symbol || "NIFTY"
    const spotPrice = data?.spot_price
    const loading = Boolean(data?.loading)
    const error = data?.error || ""

    const maxOi = Math.max(
        1,
        ...strikes.map((strike: any) => Math.max(strike.call_oi || 0, strike.put_oi || 0))
    )

    return (

        <div style={styles.container}>

            <div style={styles.headerRow}>
                <div>
                    <div style={styles.header}>Option Chain</div>
                    <div style={styles.subheader}>Expanded strike ladder with balanced call and put depth.</div>
                </div>

                <div style={styles.metaCard}>
                    <span>{symbol}</span>
                    <span>Spot {formatNumber(spotPrice)}</span>
                    <span>{expiry ? `Exp ${expiry}` : "No expiry"}</span>
                    {loading && strikes.length > 0 && <span style={styles.refreshBadge}>Refreshing</span>}
                </div>
            </div>

            <div style={styles.tableHeader}>
                <span>Calls</span>
                <span>Strike</span>
                <span>Puts</span>
            </div>

            <div style={styles.grid}>
                {loading && strikes.length === 0 && (
                    <div style={styles.stateText}>
                        Loading option chain...
                    </div>
                )}

                {!loading && error && strikes.length === 0 && (
                    <div style={styles.stateText}>
                        {error}
                    </div>
                )}

                {!loading && !error && strikes.length === 0 && (
                    <div style={styles.stateText}>
                        Option chain unavailable for this symbol right now.
                    </div>
                )}

                {strikes.map((strikeRow: any, index: number) => {
                    const callIntensity = Math.min((strikeRow.call_oi || 0) / maxOi, 1)
                    const putIntensity = Math.min((strikeRow.put_oi || 0) / maxOi, 1)
                    const isAtm = atmStrike === strikeRow.strike

                    return (
                        <div
                            key={`${strikeRow.strike}-${index}`}
                            style={isAtm ? styles.rowAtm : styles.row}
                        >
                            <div
                                style={{
                                    ...styles.sideCell,
                                    background: `linear-gradient(90deg, rgba(255,128,151,${0.18 + callIntensity * 0.54}) 0%, rgba(255,128,151,0.05) 100%)`
                                }}
                            >
                                <div style={styles.sideTopRow}>
                                    <span style={styles.sideLabel}>LTP</span>
                                    <span style={styles.priceText}>{formatNumber(strikeRow.call_ltp)}</span>
                                </div>
                                <div style={styles.sideBottomRow}>
                                    <span>OI {formatInteger(strikeRow.call_oi)}</span>
                                    <span>VOL {formatInteger(strikeRow.call_volume)}</span>
                                </div>
                            </div>

                            <div style={styles.strikeCell}>
                                <div style={styles.strikeValue}>{formatInteger(strikeRow.strike)}</div>
                                {isAtm && <div style={styles.atmBadge}>ATM</div>}
                            </div>

                            <div
                                style={{
                                    ...styles.sideCell,
                                    background: `linear-gradient(270deg, rgba(114,255,210,${0.18 + putIntensity * 0.54}) 0%, rgba(114,255,210,0.05) 100%)`
                                }}
                            >
                                <div style={styles.sideTopRow}>
                                    <span style={styles.sideLabel}>LTP</span>
                                    <span style={styles.priceText}>{formatNumber(strikeRow.put_ltp)}</span>
                                </div>
                                <div style={styles.sideBottomRow}>
                                    <span>OI {formatInteger(strikeRow.put_oi)}</span>
                                    <span>VOL {formatInteger(strikeRow.put_volume)}</span>
                                </div>
                            </div>
                        </div>
                    )
                })}
            </div>

        </div>
    )
}

export default OptionChainHeatmap


const styles: any = {

    container: {
        height: "100%",
        background: "linear-gradient(180deg, rgba(5, 10, 20, 0.55) 0%, rgba(2, 5, 12, 0.65) 100%)",
        backdropFilter: "blur(12px)",
        padding: 20,
        borderRadius: 16,
        display: "flex",
        flexDirection: "column",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), 0 0 30px rgba(100,140,200,0.05)",
        border: "1px solid rgba(150, 180, 220, 0.15)",
        minHeight: 0,
        overflow: "hidden"
    },

    headerRow: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: 14,
        marginBottom: 12,
        flexWrap: "wrap"
    },

    header: {
        fontSize: 20,
        fontWeight: 700,
        color: spaceTheme.textSecondary,
        fontFamily: spaceTheme.titleFamily,
        letterSpacing: "0.04em"
    },

    subheader: {
        marginTop: 4,
        color: spaceTheme.textMuted,
        fontSize: 12
    },

    metaCard: {
        display: "flex",
        gap: 10,
        fontSize: 12,
        color: spaceTheme.textDim,
        flexWrap: "wrap",
        justifyContent: "flex-end",
        alignItems: "center",
        padding: "8px 10px",
        ...innerShell,
        borderRadius: 12
    },

    refreshBadge: {
        padding: "3px 8px",
        borderRadius: 999,
        background: "rgba(114, 255, 210, 0.14)",
        color: spaceTheme.positive,
        border: "1px solid rgba(114, 255, 210, 0.14)",
        fontWeight: 700
    },

    tableHeader: {
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) 124px minmax(0, 1fr)",
        marginBottom: 6,
        color: spaceTheme.textMuted,
        fontSize: 11,
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        paddingRight: 6
    },

    grid: {
        flex: 1,
        overflowY: "auto",
        overflowX: "hidden",
        display: "flex",
        flexDirection: "column",
        gap: 6,
        minHeight: 0,
        paddingRight: 6
    },

    row: {
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) 124px minmax(0, 1fr)",
        gap: 8,
        minHeight: 64
    },

    rowAtm: {
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) 124px minmax(0, 1fr)",
        gap: 8,
        minHeight: 30,
        boxShadow: "inset 0 0 0 1px rgba(255, 214, 124, 0.2)",
        borderRadius: 12
    },

    sideCell: {
        padding: "10px 12px",
        borderRadius: 12,
        color: spaceTheme.textPrimary,
        border: "1px solid rgba(149, 214, 255, 0.08)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: 6,
        minWidth: 0
    },

    sideTopRow: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 10
    },

    sideBottomRow: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 10,
        color: spaceTheme.textSecondary,
        fontSize: 11.5,
        flexWrap: "wrap"
    },

    sideLabel: {
        fontSize: 11,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: spaceTheme.textMuted
    },

    strikeCell: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        ...innerShell,
        borderRadius: 12,
        color: spaceTheme.textSecondary,
        minHeight: 0
    },

    strikeValue: {
        fontSize: 16,
        fontWeight: 700
    },

    atmBadge: {
        marginTop: 4,
        padding: "2px 8px",
        borderRadius: 999,
        fontSize: 10,
        fontWeight: 700,
        background: "linear-gradient(180deg, rgba(255, 224, 163, 0.98) 0%, rgba(255, 198, 104, 0.98) 100%)",
        color: "#08101f",
        boxShadow: "0 0 12px rgba(255, 210, 133, 0.18)"
    },

    priceText: {
        fontSize: 14,
        fontWeight: 700
    },

    stateText: {
        flex: 1,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: spaceTheme.textMuted,
        fontSize: 13,
        textAlign: "center",
        padding: 12
    }

}
