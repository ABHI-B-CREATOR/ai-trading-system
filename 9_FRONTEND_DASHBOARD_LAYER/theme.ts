export const spaceTheme = {
    fontFamily: '"Bahnschrift", "Trebuchet MS", "Segoe UI", sans-serif',
    titleFamily: '"Bahnschrift SemiBold", "Bahnschrift", "Trebuchet MS", sans-serif',
    pageBase: "#000000",
    // Edge-on galaxy background - pure black with centered galaxy
    pageBackground: "linear-gradient(180deg, #000000 0%, #000000 100%)",
    // Scattered stars across the whole screen
    starfield: [
        "radial-gradient(circle, rgba(255,255,255,0.95) 0 0.8px, transparent 1.6px)",
        "radial-gradient(circle, rgba(255,255,255,0.85) 0 1.0px, transparent 2.0px)",
        "radial-gradient(circle, rgba(220,235,255,0.75) 0 1.2px, transparent 2.2px)",
        "radial-gradient(circle, rgba(255,255,255,0.55) 0 0.6px, transparent 1.4px)",
        "radial-gradient(circle, rgba(200,220,255,0.45) 0 0.7px, transparent 1.5px)",
        "radial-gradient(circle, rgba(255,255,255,0.35) 0 0.5px, transparent 1.2px)"
    ].join(", "),
    // Galaxy core - bright white/blue center glow
    galaxyCore: [
        "radial-gradient(ellipse 45% 8% at 50% 50%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.7) 15%, rgba(200,220,255,0.4) 35%, rgba(150,180,220,0.15) 55%, transparent 80%)",
        "radial-gradient(ellipse 55% 12% at 50% 50%, rgba(180,200,240,0.5) 0%, rgba(150,180,220,0.25) 40%, transparent 70%)",
        "radial-gradient(ellipse 70% 18% at 50% 50%, rgba(120,150,200,0.25) 0%, rgba(80,110,160,0.1) 50%, transparent 80%)"
    ].join(", "),
    // Galaxy dust lane - dark band across the center
    galaxyDust: [
        "linear-gradient(0deg, transparent 42%, rgba(0,0,0,0.7) 46%, rgba(20,25,35,0.5) 48%, rgba(0,0,0,0.6) 50%, rgba(30,35,45,0.4) 52%, rgba(0,0,0,0.7) 54%, transparent 58%)"
    ].join(", "),
    // Galaxy outer halo - subtle blue glow extending outward
    galaxyHalo: [
        "radial-gradient(ellipse 90% 25% at 50% 50%, rgba(100,130,180,0.08) 0%, rgba(70,100,150,0.04) 50%, transparent 80%)",
        "radial-gradient(ellipse 120% 35% at 50% 50%, rgba(60,90,140,0.04) 0%, transparent 70%)"
    ].join(", "),
    // Transparent panels to show galaxy through
    panelBackground: "linear-gradient(180deg, rgba(5, 8, 15, 0.65) 0%, rgba(3, 5, 10, 0.75) 100%)",
    panelBorder: "1px solid rgba(150, 180, 220, 0.18)",
    panelShadow: "inset 0 1px 0 rgba(255,255,255,0.06), 0 20px 44px rgba(0,0,0,0.5), 0 0 40px rgba(100, 140, 200, 0.08)",
    innerSurface: "linear-gradient(180deg, rgba(8, 12, 22, 0.7) 0%, rgba(4, 6, 12, 0.8) 100%)",
    innerBorder: "1px solid rgba(140, 170, 220, 0.15)",
    textPrimary: "#f7f6ff",
    textSecondary: "#d7dcf4",
    textMuted: "#98a4c7",
    textDim: "#707aa0",
    accent: "#82eaff",
    accentStrong: "#fbfcff",
    accentLine: "#4a447a",
    accentSoft: "rgba(164, 147, 255, 0.16)",
    positive: "#7dffd9",
    negative: "#ff88b0",
    warning: "#ffd38b",
    neutral: "#d9def1"
} as const

export const panelShell = {
    background: spaceTheme.panelBackground,
    border: spaceTheme.panelBorder,
    borderRadius: 18,
    boxShadow: spaceTheme.panelShadow,
    backdropFilter: "blur(18px)",
    minHeight: 0,
    minWidth: 0,
    overflow: "hidden"
} as const

export const innerShell = {
    background: spaceTheme.innerSurface,
    border: spaceTheme.innerBorder,
    borderRadius: 14,
    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05), 0 14px 26px rgba(0,0,0,0.24)",
    minHeight: 0,
    minWidth: 0
} as const

export const chartTheme = {
    background: "#f6f8fb",
    bullish: "#089981",
    bearish: "#f23645",
    gridHorizontal: "rgba(92, 104, 131, 0.24)",
    gridVertical: "rgba(92, 104, 131, 0.14)",
    axisText: "#4b5568",
    priceLine: "#1f9cf0",
    crosshairPrimary: "rgba(86, 97, 122, 0.56)",
    crosshairSecondary: "rgba(86, 97, 122, 0.36)",
    axisPanel: "#f2f5fa",
    axisBorder: "rgba(92, 104, 131, 0.26)",
    currentPriceGlow: "rgba(31, 156, 240, 0.32)",
    hoverFill: "rgba(61, 83, 127, 0.10)"
} as const
