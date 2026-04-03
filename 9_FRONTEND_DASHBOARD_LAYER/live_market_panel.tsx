import React, { ReactElement, useEffect, useLayoutEffect, useRef, useState } from "react"
import { chartTheme, innerShell, panelShell, spaceTheme } from "./theme"

type Candle = {
    open?: number
    high?: number
    low?: number
    close?: number
    volume?: number
    time?: string
}

type HoverPayload = {
    candleIndex: number | null
    candle: Candle | null
    timeLabel: string
    hoveredPrice: number | null
}

type ViewportState = {
    start: number
    size: number
}

const INTERVAL_OPTIONS = [
    { value: "minute", label: "1m" },
    { value: "5minute", label: "5m" },
    { value: "15minute", label: "15m" },
    { value: "60minute", label: "1h" },
    { value: "day", label: "1D" }
]

const X_AXIS_HEIGHT = 38
const DEFAULT_AXIS_WIDTH = 102
const MIN_AXIS_WIDTH = 84
const MAX_AXIS_WIDTH = 180
const MIN_PLOT_WIDTH = 280
const MIN_VISIBLE_CANDLES = 24
const MIN_CHART_HEIGHT = 260
const MAX_CHART_HEIGHT = 680
const CHART_PADDING = 10
const MAX_HOVER_FPS = 60

const getElementWidth = (element: HTMLElement | null): number => {
    if (!element) {
        return 0
    }

    const rectWidth = element.getBoundingClientRect().width
    if (Number.isFinite(rectWidth) && rectWidth > 0) {
        return rectWidth
    }

    return element.clientWidth
}

const toNumber = (value: any): number | null => {
    if (typeof value === "number" && Number.isFinite(value)) {
        return value
    }

    if (typeof value === "string") {
        const parsed = Number(value)
        if (Number.isFinite(parsed)) {
            return parsed
        }
    }

    return null
}

const parseChartDate = (value: string | undefined): Date | null => {
    if (!value) {
        return null
    }

    const normalizedValue = /(?:Z|[+-]\d{2}:\d{2})$/.test(value)
        ? value
        : `${value}Z`
    const parsed = new Date(normalizedValue)

    return Number.isNaN(parsed.getTime()) ? null : parsed
}

const formatPrice = (value: any): string => {
    const number = toNumber(value)
    if (number === null) {
        return "--"
    }

    return number.toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })
}

const formatVolume = (value: any): string => {
    const number = toNumber(value)
    if (number === null) {
        return "--"
    }

    return number.toLocaleString("en-IN")
}

const formatChange = (value: any): string => {
    const number = toNumber(value)
    if (number === null) {
        return "--"
    }

    return `${number >= 0 ? "+" : ""}${number.toFixed(2)}%`
}

const getPercentChange = (currentValue: any, previousValue: any): number | null => {
    const current = toNumber(currentValue)
    const previous = toNumber(previousValue)

    if (current === null || previous === null || previous === 0) {
        return null
    }

    return ((current - previous) / previous) * 100
}

const formatStatusLabel = (value: any): string => {
    if (!value) {
        return "Unknown"
    }

    return String(value)
        .replace(/_/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

const getStatusAppearance = (value: any): { background: string, color: string, border: string } => {
    const normalized = String(value || "unknown").toLowerCase()

    if (["running", "live_connected", "connected", "open", "valid"].includes(normalized)) {
        return {
            background: "rgba(125, 255, 217, 0.16)",
            color: spaceTheme.positive,
            border: "1px solid rgba(125, 255, 217, 0.24)"
        }
    }

    if (["closed", "pre_open", "unknown"].includes(normalized)) {
        return {
            background: "rgba(217, 222, 241, 0.12)",
            color: spaceTheme.neutral,
            border: "1px solid rgba(217, 222, 241, 0.18)"
        }
    }

    if (["demo_fallback", "starting", "checking", "connecting", "paper", "demo", "live", "not_required"].includes(normalized)) {
        return {
            background: "rgba(255, 211, 139, 0.16)",
            color: spaceTheme.warning,
            border: "1px solid rgba(255, 211, 139, 0.24)"
        }
    }

    if (["error", "token_expired", "expired", "invalid", "missing", "disconnected", "stopped"].includes(normalized)) {
        return {
            background: "rgba(255, 136, 176, 0.16)",
            color: spaceTheme.negative,
            border: "1px solid rgba(255, 136, 176, 0.24)"
        }
    }

    return {
        background: "rgba(145, 238, 255, 0.12)",
        color: spaceTheme.accent,
        border: "1px solid rgba(145, 238, 255, 0.12)"
    }
}

const clamp = (value: number, min: number, max: number): number => {
    if (max < min) {
        return min
    }

    return Math.min(Math.max(value, min), max)
}

const getRightOffsetSlots = (timeframe: string, visibleSize: number): number => {
    const ratio = timeframe === "day"
        ? 0.12
        : timeframe === "60minute"
            ? 0.11
            : 0.1
    const minimumOffset = timeframe === "day" ? 8 : 5
    const maximumOffset = timeframe === "day" ? 16 : 10

    return Math.min(
        Math.max(Math.round(visibleSize * ratio), minimumOffset),
        maximumOffset
    )
}

const clampViewport = (viewport: ViewportState, totalCandles: number, timeframe: string): ViewportState => {
    if (totalCandles <= 0) {
        return { start: 0, size: 0 }
    }

    const minimumSize = Math.min(MIN_VISIBLE_CANDLES, totalCandles)
    const size = Math.round(clamp(viewport.size, minimumSize, totalCandles))
    const rightOffset = Math.min(getRightOffsetSlots(timeframe, size), Math.max(size - 2, 0))
    const maxStart = Math.max(totalCandles - size + rightOffset, 0)

    return {
        start: clamp(viewport.start, 0, maxStart),
        size
    }
}

const getDefaultVisibleCount = (timeframe: string, totalCandles: number, plotWidth: number = MIN_PLOT_WIDTH): number => {
    if (totalCandles <= 0) {
        return 0
    }

    const baseline = timeframe === "day"
        ? 90
        : timeframe === "60minute"
            ? 78
            : timeframe === "15minute"
                ? 68
                : timeframe === "5minute"
                    ? 64
                    : 56
    const targetCandlePitch = timeframe === "day"
        ? 12.5
        : timeframe === "60minute"
            ? 11.5
            : timeframe === "15minute"
                ? 10.75
                : timeframe === "5minute"
                    ? 10.25
                    : 9.75
    const widthBased = Math.floor(Math.max(plotWidth, MIN_PLOT_WIDTH) / targetCandlePitch)
    const preferred = Math.max(baseline, widthBased)

    return clamp(Math.min(preferred, totalCandles), Math.min(MIN_VISIBLE_CANDLES, totalCandles), totalCandles)
}

const buildDefaultViewport = (candles: Candle[], timeframe: string, plotWidth: number = MIN_PLOT_WIDTH): ViewportState => {
    if (candles.length === 0) {
        return { start: 0, size: 0 }
    }

    const size = getDefaultVisibleCount(timeframe, candles.length, plotWidth)
    const rightOffset = Math.min(getRightOffsetSlots(timeframe, size), Math.max(size - 2, 0))
    return {
        start: Math.max(candles.length - size + rightOffset, 0),
        size
    }
}

const formatTimeLabel = (value: string | undefined, timeframe: string): string => {
    const date = parseChartDate(value)
    if (!date) {
        return ""
    }

    if (timeframe === "day" || timeframe === "60minute") {
        return date.toLocaleDateString("en-IN", {
            day: "2-digit",
            month: "short"
        })
    }

    return date.toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit"
    })
}

const formatExactTimestamp = (value: string | undefined): string => {
    const date = parseChartDate(value)
    if (!date) {
        return ""
    }

    return date.toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    })
}

const CandleChart = ({
    candles,
    currentPrice,
    timeframe,
    loading,
    error,
    axisWidth,
    onAxisWidthChange,
    onHoverCandleChange,
    chartHeight,
    compact
}: {
    candles: Candle[]
    currentPrice: number | null
    timeframe: string
    loading: boolean
    error: string
    axisWidth: number
    onAxisWidthChange: (width: number) => void
    onHoverCandleChange: (payload: HoverPayload | null) => void
    chartHeight: number
    compact: boolean
}): ReactElement => {

    const plotRef = useRef<HTMLDivElement | null>(null)
    const dragRef = useRef<{ pointerId: number, lastX: number, lastTime: number, velocity: number } | null>(null)
    const resizeRef = useRef<{ pointerId: number, startX: number, startWidth: number } | null>(null)
    const inertiaRef = useRef<number | null>(null)
    const hoverTimerRef = useRef<number | null>(null)
    const lastHoverUpdateRef = useRef(0)
    const hoverPointRef = useRef<{ clientX: number, clientY: number } | null>(null)
    const viewportRef = useRef<ViewportState>(buildDefaultViewport(candles, timeframe))
    const previousTimeframeRef = useRef(timeframe)
    const hasUserAdjustedViewRef = useRef(false)
    const [availableWidth, setAvailableWidth] = useState(MIN_PLOT_WIDTH)
    const [viewport, setViewport] = useState<ViewportState>(() => buildDefaultViewport(candles, timeframe))
    const [hoverState, setHoverState] = useState<{ index: number, y: number, hoveredPrice: number } | null>(null)

    const clearHover = (): void => {
        hoverPointRef.current = null
        setHoverState(null)
        onHoverCandleChange(null)
    }

    const commitViewport = (nextViewport: ViewportState | ((current: ViewportState) => ViewportState)): void => {
        setViewport((current) => {
            const resolved = typeof nextViewport === "function" ? nextViewport(current) : nextViewport
            const clamped = clampViewport(resolved, candles.length, timeframe)
            viewportRef.current = clamped
            return clamped
        })
    }

    const cancelInertia = (): void => {
        if (inertiaRef.current !== null) {
            window.cancelAnimationFrame(inertiaRef.current)
            inertiaRef.current = null
        }
    }

    const cancelHoverFrame = (): void => {
        if (hoverTimerRef.current !== null) {
            window.clearTimeout(hoverTimerRef.current)
            hoverTimerRef.current = null
        }
    }

    const plotHeight = Math.max(chartHeight - X_AXIS_HEIGHT, 180)
    const resolvedAxisWidth = clamp(axisWidth, MIN_AXIS_WIDTH, MAX_AXIS_WIDTH)
    const measuredPlotWidth = getElementWidth(plotRef.current)
    const plotWidth = Math.max(measuredPlotWidth || availableWidth, MIN_PLOT_WIDTH)
    const visibleViewport = clampViewport(viewport, candles.length, timeframe)
    const slotWidth = plotWidth / Math.max(visibleViewport.size || 1, 1)
    const bodyWidthRatio = timeframe === "day"
        ? 0.52
        : timeframe === "60minute"
            ? 0.56
            : 0.6
    const candleBodyWidth = clamp(
        slotWidth * bodyWidthRatio * (compact ? 0.92 : 1),
        2.4,
        timeframe === "day"
            ? (compact ? 11 : 13)
            : (compact ? 12 : 15)
    )
    const wickStrokeWidth = clamp(candleBodyWidth * 0.14, 1, 1.8)
    const visibleStart = Math.max(Math.floor(visibleViewport.start) - 1, 0)
    const visibleEnd = Math.min(Math.ceil(visibleViewport.start + visibleViewport.size) + 1, candles.length)
    const visibleCandles = candles.slice(visibleStart, visibleEnd)

    const priceValues = visibleCandles.flatMap((candle) => {
        const high = toNumber(candle.high ?? candle.close ?? candle.open)
        const low = toNumber(candle.low ?? candle.close ?? candle.open)
        return [high, low].filter((value): value is number => value !== null)
    })

    if (currentPrice !== null) {
        priceValues.push(currentPrice)
    }

    const rawMax = priceValues.length > 0 ? Math.max(...priceValues) : 1
    const rawMin = priceValues.length > 0 ? Math.min(...priceValues) : Math.max(rawMax - 1, 0)
    const paddingRatio = timeframe === "day"
        ? 0.12
        : timeframe === "60minute"
            ? 0.1
            : 0.085
    const padding = Math.max((rawMax - rawMin) * paddingRatio, 0.45)
    const max = rawMax + padding
    const min = Math.max(rawMin - padding, 0)
    const range = Math.max(max - min, 1)
    const drawableHeight = Math.max(plotHeight - CHART_PADDING * 2, 1)
    const axisLabelCount = Math.round(clamp(Math.floor(plotHeight / 78) + 2, 4, 7))
    const axisValues = Array.from({ length: axisLabelCount }, (_, index) => max - (range / (axisLabelCount - 1)) * index)
    const targetLabelGap = timeframe === "day" ? 220 : 190
    const xAxisLabelCount = Math.round(clamp(Math.floor(plotWidth / targetLabelGap) + 1, 3, timeframe === "day" ? 6 : 5))
    const xAxisLabels = Array.from({ length: xAxisLabelCount }, (_, index) => {
        const ratio = xAxisLabelCount === 1 ? 0 : index / (xAxisLabelCount - 1)
        const candleIndex = clamp(
            Math.round(visibleViewport.start + ratio * Math.max(visibleViewport.size - 1, 0)),
            0,
            Math.max(candles.length - 1, 0)
        )

        return {
            key: `${candleIndex}-${index}`,
            x: ((candleIndex - visibleViewport.start) + 0.5) * slotWidth,
            label: formatTimeLabel(candles[candleIndex]?.time, timeframe)
        }
    }).filter((item, index, items) => {
        if (!item.label) {
            return false
        }

        if (index === 0) {
            return true
        }

        const previous = items[index - 1]
        return previous
            ? item.label !== previous.label && Math.abs(item.x - previous.x) >= (timeframe === "day" ? 88 : 74)
            : true
    }).map((item, index, items) => {
        const isFirst = index === 0
        const isLast = index === items.length - 1
        const edgeInset = 12
        const midInset = 36
        const textAnchor: "start" | "middle" | "end" = isFirst ? "start" : (isLast ? "end" : "middle")

        return {
            ...item,
            textAnchor,
            x: clamp(item.x, isFirst ? edgeInset : midInset, isLast ? plotWidth - edgeInset : plotWidth - midInset)
        }
    })

    const yForPrice = (price: number): number => {
        const ratio = (max - price) / range
        return CHART_PADDING + ratio * drawableHeight
    }

    const priceForY = (y: number): number => {
        const ratio = (clamp(y, CHART_PADDING, CHART_PADDING + drawableHeight) - CHART_PADDING) / drawableHeight
        return max - ratio * range
    }

    const getCurrentPlotWidth = (): number => {
        return Math.max(getElementWidth(plotRef.current) || plotWidth, MIN_PLOT_WIDTH)
    }

    const getPlotPoint = (clientX: number, clientY: number): { x: number, y: number } | null => {
        const element = plotRef.current
        if (!element) {
            return null
        }

        const rect = element.getBoundingClientRect()
        return {
            x: clamp(clientX - rect.left, 0, rect.width),
            y: clamp(clientY - rect.top, 0, plotHeight)
        }
    }

    const applyHover = (clientX: number, clientY: number): void => {
        const point = getPlotPoint(clientX, clientY)
        if (!point || candles.length === 0 || visibleViewport.size === 0) {
            clearHover()
            return
        }

        const currentPlotWidth = getCurrentPlotWidth()
        const currentSlotWidth = currentPlotWidth / Math.max(visibleViewport.size || 1, 1)

        const hoveredIndex = clamp(
            Math.round(visibleViewport.start + point.x / Math.max(currentSlotWidth, 1) - 0.5),
            0,
            candles.length - 1
        )

        const candle = candles[hoveredIndex] || null
        const hoveredPrice = priceForY(point.y)

        setHoverState({
            index: hoveredIndex,
            y: point.y,
            hoveredPrice
        })

        onHoverCandleChange({
            candleIndex: hoveredIndex,
            candle,
            timeLabel: formatExactTimestamp(candle?.time),
            hoveredPrice
        })
    }

    const updateHover = (clientX: number, clientY: number): void => {
        hoverPointRef.current = { clientX, clientY }

        if (hoverTimerRef.current !== null) {
            return
        }

        const frameBudget = 1000 / MAX_HOVER_FPS
        const elapsed = performance.now() - lastHoverUpdateRef.current
        const delay = Math.max(frameBudget - elapsed, 0)

        hoverTimerRef.current = window.setTimeout(() => {
            hoverTimerRef.current = null
            const point = hoverPointRef.current
            if (!point) {
                return
            }

            lastHoverUpdateRef.current = performance.now()
            applyHover(point.clientX, point.clientY)
        }, delay)
    }

    useLayoutEffect(() => {
        const element = plotRef.current
        if (!element) {
            return
        }

        const updateWidth = (): void => {
            const nextWidth = getElementWidth(element)
            if (nextWidth > 0) {
                setAvailableWidth((current) => Math.abs(current - nextWidth) >= 1 ? nextWidth : current)
            }
        }

        updateWidth()
        const firstFrame = window.requestAnimationFrame(updateWidth)
        const secondFrame = window.requestAnimationFrame(() => {
            window.requestAnimationFrame(updateWidth)
        })

        window.addEventListener("resize", updateWidth)

        if (typeof ResizeObserver === "undefined") {
            return () => {
                window.cancelAnimationFrame(firstFrame)
                window.cancelAnimationFrame(secondFrame)
                window.removeEventListener("resize", updateWidth)
            }
        }

        const observer = new ResizeObserver(() => {
            updateWidth()
        })

        observer.observe(element)
        if (element.parentElement) {
            observer.observe(element.parentElement)
        }

        return () => {
            observer.disconnect()
            window.cancelAnimationFrame(firstFrame)
            window.cancelAnimationFrame(secondFrame)
            window.removeEventListener("resize", updateWidth)
        }
    }, [resolvedAxisWidth])

    useEffect(() => {
        const timeframeChanged = previousTimeframeRef.current !== timeframe

        if (candles.length === 0) {
            const emptyViewport = { start: 0, size: 0 }
            viewportRef.current = emptyViewport
            setViewport(emptyViewport)
            clearHover()
            previousTimeframeRef.current = timeframe
            return
        }

        if (timeframeChanged || !hasUserAdjustedViewRef.current) {
            const nextViewport = buildDefaultViewport(candles, timeframe, plotWidth)
            viewportRef.current = nextViewport
            setViewport(nextViewport)
        } else {
            const nextViewport = clampViewport(viewportRef.current, candles.length, timeframe)
            viewportRef.current = nextViewport
            setViewport(nextViewport)
        }

        if (timeframeChanged) {
            clearHover()
        }

        previousTimeframeRef.current = timeframe
    }, [candles, plotWidth, timeframe, onHoverCandleChange])

    useEffect(() => {
        const point = hoverPointRef.current
        if (!point || dragRef.current) {
            return
        }

        applyHover(point.clientX, point.clientY)
    }, [candles, plotHeight, plotWidth, timeframe, visibleViewport.size, visibleViewport.start])

    useEffect(() => {
        return () => {
            cancelInertia()
            cancelHoverFrame()
        }
    }, [])

    const startInertia = (initialVelocity: number): void => {
        cancelInertia()

        let velocity = initialVelocity
        let previousFrame = performance.now()

        const tick = (now: number): void => {
            const elapsed = now - previousFrame
            previousFrame = now

            if (Math.abs(velocity) < 0.003) {
                inertiaRef.current = null
                return
            }

            commitViewport((current) => ({
                ...current,
                start: current.start + velocity * elapsed
            }))

            velocity *= 0.92
            inertiaRef.current = window.requestAnimationFrame(tick)
        }

        inertiaRef.current = window.requestAnimationFrame(tick)
    }

    const handleWheel = (event: React.WheelEvent<HTMLDivElement>): void => {
        if (candles.length <= Math.min(MIN_VISIBLE_CANDLES, candles.length)) {
            return
        }

        event.preventDefault()
        cancelInertia()
        hasUserAdjustedViewRef.current = true

        const point = getPlotPoint(event.clientX, event.clientY)
        const currentPlotWidth = getCurrentPlotWidth()
        const anchorRatio = point ? point.x / Math.max(currentPlotWidth, 1) : 1
        const anchorIndex = visibleViewport.start + anchorRatio * visibleViewport.size
        const zoomFactor = Math.exp(event.deltaY * 0.00065)

        commitViewport((current) => {
            const minimumSize = Math.min(MIN_VISIBLE_CANDLES, candles.length)
            const nextSize = Math.round(clamp(current.size * zoomFactor, minimumSize, candles.length))
            const cursorRatio = current.size > 0 ? (anchorIndex - current.start) / current.size : 1

            return {
                start: anchorIndex - cursorRatio * nextSize,
                size: nextSize
            }
        })

        updateHover(event.clientX, event.clientY)
    }

    const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>): void => {
        if (candles.length === 0) {
            return
        }

        cancelInertia()
        const point = getPlotPoint(event.clientX, event.clientY)
        if (!point) {
            return
        }

        dragRef.current = {
            pointerId: event.pointerId,
            lastX: point.x,
            lastTime: performance.now(),
            velocity: 0
        }

        event.currentTarget.setPointerCapture(event.pointerId)
        updateHover(event.clientX, event.clientY)
    }

    const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>): void => {
        updateHover(event.clientX, event.clientY)

        const dragState = dragRef.current
        if (!dragState || dragState.pointerId !== event.pointerId) {
            return
        }

        const point = getPlotPoint(event.clientX, event.clientY)
        if (!point) {
            return
        }

        const now = performance.now()
        const deltaX = point.x - dragState.lastX
        if (Math.abs(deltaX) < 0.2) {
            return
        }

        const currentSlotWidth = getCurrentPlotWidth() / Math.max(visibleViewport.size || 1, 1)
        const deltaStart = -(deltaX / Math.max(currentSlotWidth, 1))
        hasUserAdjustedViewRef.current = true

        commitViewport((current) => ({
            ...current,
            start: current.start + deltaStart
        }))

        dragState.velocity = deltaStart / Math.max(now - dragState.lastTime, 16)
        dragState.lastX = point.x
        dragState.lastTime = now
    }

    const releaseDrag = (event: React.PointerEvent<HTMLDivElement>): void => {
        const dragState = dragRef.current
        if (!dragState || dragState.pointerId !== event.pointerId) {
            return
        }

        dragRef.current = null
        event.currentTarget.releasePointerCapture(event.pointerId)

        if (Math.abs(dragState.velocity) > 0.003) {
            startInertia(dragState.velocity)
        }
    }

    const hoverX = hoverState
        ? ((hoverState.index - visibleViewport.start) + 0.5) * slotWidth
        : null
    const showHover = hoverState !== null && hoverX !== null && hoverX >= 0 && hoverX <= plotWidth
    const currentPriceY = currentPrice !== null ? yForPrice(currentPrice) : null
    const hoveredPriceY = showHover ? clamp(hoverState.y, 6, plotHeight - 22) : null
    const currentPriceTop = currentPriceY !== null ? clamp(currentPriceY - 11, 6, plotHeight - 22) : null

    if (!candles || candles.length === 0) {
        return (
            <div style={styles.emptyChart}>
                {loading ? "Loading chart history..." : (error || "Waiting for chart data...")}
            </div>
        )
    }

    return (
        <div style={styles.chartViewport}>
            <div
                ref={plotRef}
                style={styles.plotSurface}
                onWheel={handleWheel}
                onDoubleClick={() => {
                    cancelInertia()
                    hasUserAdjustedViewRef.current = false
                    const nextViewport = buildDefaultViewport(candles, timeframe, plotWidth)
                    viewportRef.current = nextViewport
                    setViewport(nextViewport)
                }}
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onMouseMove={(event) => {
                    updateHover(event.clientX, event.clientY)
                }}
                onPointerUp={releaseDrag}
                onPointerCancel={releaseDrag}
                onPointerLeave={() => {
                    if (!dragRef.current) {
                        clearHover()
                    }
                }}
                onMouseLeave={() => {
                    if (!dragRef.current) {
                        clearHover()
                    }
                }}
            >
                <svg
                    viewBox={`0 0 ${plotWidth} ${chartHeight}`}
                    preserveAspectRatio="none"
                    style={styles.candleSvg}
                >
                    <rect x={0} y={0} width={plotWidth} height={plotHeight} fill={chartTheme.background} />

                    {axisValues.map((value, index) => {
                        const y = yForPrice(value)
                        return (
                            <line
                                key={`axis-${index}`}
                                x1={0}
                                y1={y}
                                x2={plotWidth}
                                y2={y}
                                stroke={chartTheme.gridHorizontal}
                                strokeWidth={1}
                                strokeDasharray="2 7"
                            />
                        )
                    })}

                    {xAxisLabels.map((item) => (
                        <line
                            key={`grid-x-${item.key}`}
                            x1={item.x}
                            y1={0}
                            x2={item.x}
                            y2={plotHeight}
                            stroke={chartTheme.gridVertical}
                            strokeWidth={1}
                            strokeDasharray="2 7"
                        />
                    ))}

                    {xAxisLabels.map((item) => (
                        <g key={`x-${item.key}`}>
                            <text
                                x={item.x}
                                y={plotHeight + 22}
                                textAnchor={item.textAnchor}
                                dominantBaseline="middle"
                                fill={chartTheme.axisText}
                                fontSize="11"
                                fontWeight="600"
                            >
                                {item.label}
                            </text>
                        </g>
                    ))}

                    {visibleCandles.map((candle, offset) => {
                        const index = visibleStart + offset
                        const open = toNumber(candle.open ?? candle.close)
                        const high = toNumber(candle.high ?? candle.close ?? candle.open)
                        const low = toNumber(candle.low ?? candle.close ?? candle.open)
                        const close = toNumber(candle.close ?? candle.open)

                        if (open === null || high === null || low === null || close === null) {
                            return null
                        }

                        const x = ((index - visibleViewport.start) + 0.5) * slotWidth
                        if (x < -slotWidth || x > plotWidth + slotWidth) {
                            return null
                        }

                        const openY = yForPrice(open)
                        const highY = yForPrice(high)
                        const lowY = yForPrice(low)
                        const closeY = yForPrice(close)
                        const bodyTop = Math.min(openY, closeY)
                        const bodyBottom = Math.max(openY, closeY)
                        const bodyHeight = Math.max(Math.abs(closeY - openY), 2.8)
                        const color = close >= open ? chartTheme.bullish : chartTheme.bearish
                        const wickX = Math.round(x) + 0.5
                        const snappedBodyWidth = Math.max(Math.round(candleBodyWidth), 3)
                        const isHovered = hoverState?.index === index
                        const renderedBodyWidth = Math.max(snappedBodyWidth + (isHovered ? 1 : 0), 2)
                        const snappedBodyX = Math.round(wickX - renderedBodyWidth / 2)
                        const snappedBodyTop = Math.round(bodyTop)
                        const snappedBodyHeight = Math.max(Math.round(bodyHeight), 3)
                        const snappedBodyBottom = snappedBodyTop + snappedBodyHeight
                        const snappedHighY = Math.round(highY) + 0.5
                        const snappedLowY = Math.round(lowY) + 0.5
                        const hasUpperWick = highY < bodyTop - 0.3
                        const hasLowerWick = lowY > bodyBottom + 0.3
                        let upperWickBottom = snappedBodyTop - 0.5
                        let lowerWickTop = snappedBodyBottom + 0.5
                        let lowerWickBottom = snappedLowY

                        if (hasUpperWick && upperWickBottom <= snappedHighY) {
                            upperWickBottom = snappedHighY + 1
                        }

                        if (hasLowerWick && lowerWickBottom <= lowerWickTop) {
                            lowerWickBottom = lowerWickTop + 1
                        }

                        return (
                            <g key={`${candle.time || "candle"}-${index}`}>
                                {hasUpperWick && (
                                    <line
                                        x1={wickX}
                                        y1={snappedHighY}
                                        x2={wickX}
                                        y2={upperWickBottom}
                                        stroke={color}
                                        strokeWidth={wickStrokeWidth}
                                        shapeRendering="crispEdges"
                                        style={{
                                            opacity: isHovered ? 1 : 0.88
                                        }}
                                    />
                                )}
                                <rect
                                    x={snappedBodyX}
                                    y={snappedBodyTop}
                                    width={renderedBodyWidth}
                                    height={snappedBodyHeight}
                                    fill={color}
                                    rx={0}
                                    shapeRendering="crispEdges"
                                    style={{
                                        opacity: isHovered ? 1 : 0.92
                                    }}
                                />
                                {isHovered && (
                                    <rect
                                        x={snappedBodyX - 1.5}
                                        y={snappedBodyTop - 1.5}
                                        width={renderedBodyWidth + 3}
                                        height={snappedBodyHeight + 3}
                                        fill="none"
                                        stroke={chartTheme.hoverFill}
                                        strokeWidth={1.5}
                                        rx={1}
                                    />
                                )}
                                {hasLowerWick && (
                                    <line
                                        x1={wickX}
                                        y1={lowerWickTop}
                                        x2={wickX}
                                        y2={lowerWickBottom}
                                        stroke={color}
                                        strokeWidth={wickStrokeWidth}
                                        shapeRendering="crispEdges"
                                        style={{
                                            opacity: isHovered ? 1 : 0.88
                                        }}
                                    />
                                )}
                            </g>
                        )
                    })}

                    {currentPriceY !== null && (
                        <line
                            x1={0}
                            y1={currentPriceY}
                            x2={plotWidth}
                            y2={currentPriceY}
                            stroke={chartTheme.priceLine}
                            strokeWidth={1}
                            strokeDasharray="3 5"
                            style={{ opacity: 0.92 }}
                        />
                    )}

                    {showHover && (
                        <>
                            <line
                                x1={hoverX}
                                y1={0}
                                x2={hoverX}
                                y2={plotHeight}
                                stroke={chartTheme.crosshairPrimary}
                                strokeWidth={1}
                                strokeDasharray="4 5"
                                style={{ transition: "opacity 80ms linear" }}
                            />
                            <line
                                x1={0}
                                y1={hoverState.y}
                                x2={plotWidth}
                                y2={hoverState.y}
                                stroke={chartTheme.crosshairSecondary}
                                strokeWidth={1}
                                strokeDasharray="4 5"
                                style={{ transition: "opacity 80ms linear" }}
                            />
                        </>
                    )}
                </svg>

                {loading && (
                    <div style={styles.chartOverlay}>
                        Loading history...
                    </div>
                )}
            </div>

            <div style={{ ...styles.rightAxis, width: resolvedAxisWidth, minWidth: resolvedAxisWidth }}>
                <div
                    style={styles.axisResizeHandle}
                    onPointerDown={(event) => {
                        resizeRef.current = {
                            pointerId: event.pointerId,
                            startX: event.clientX,
                            startWidth: resolvedAxisWidth
                        }
                        event.currentTarget.setPointerCapture(event.pointerId)
                    }}
                    onPointerMove={(event) => {
                        const resizeState = resizeRef.current
                        if (!resizeState || resizeState.pointerId !== event.pointerId) {
                            return
                        }

                        onAxisWidthChange(clamp(
                            resizeState.startWidth + (resizeState.startX - event.clientX),
                            MIN_AXIS_WIDTH,
                            MAX_AXIS_WIDTH
                        ))
                    }}
                    onPointerUp={(event) => {
                        if (resizeRef.current?.pointerId === event.pointerId) {
                            resizeRef.current = null
                            event.currentTarget.releasePointerCapture(event.pointerId)
                        }
                    }}
                    onPointerCancel={(event) => {
                        if (resizeRef.current?.pointerId === event.pointerId) {
                            resizeRef.current = null
                            event.currentTarget.releasePointerCapture(event.pointerId)
                        }
                    }}
                />

                {axisValues.map((value, index) => {
                    const y = yForPrice(value)
                    return (
                        <div
                            key={`price-label-${index}`}
                            style={{
                                ...styles.axisLabel,
                                top: clamp(y - 8, 4, plotHeight - 18)
                            }}
                        >
                            {formatPrice(value)}
                        </div>
                    )
                })}

                {showHover && hoveredPriceY !== null && (
                    <div
                        style={{
                            ...styles.hoverPricePill,
                            top: hoveredPriceY
                        }}
                    >
                        {formatPrice(hoverState.hoveredPrice)}
                    </div>
                )}

                {currentPriceTop !== null && (
                    <div
                        style={{
                            ...styles.currentPricePill,
                            top: currentPriceTop
                        }}
                    >
                        {formatPrice(currentPrice)}
                    </div>
                )}
            </div>
        </div>
    )
}

const LiveMarketPanel = ({ data }: any): ReactElement => {

    const symbol = data?.symbol || "NIFTY"
    const exchange = data?.exchange || "NSE"
    const candles: Candle[] = Array.isArray(data?.candles) ? data.candles : []
    const price = toNumber(data?.ltp)
    const change = toNumber(data?.change_pct) ?? 0
    const bid = data?.bid
    const ask = data?.ask
    const volume = data?.volume
    const timeframe = data?.timeframe || "day"
    const timeframeLabel = data?.timeframeLabel || timeframe
    const chartLoading = Boolean(data?.chartLoading)
    const chartError = data?.chartError || ""
    const chartSource = data?.chartSource || "stream"
    const system = data?.system || {}
    const feedStatus = system?.feed_status || "unknown"
    const marketState = system?.market_state || "unknown"
    const dataMode = system?.data_mode || "unknown"
    const latestCandle = candles[candles.length - 1] || {}
    const [hoverPayload, setHoverPayload] = useState<HoverPayload | null>(null)
    const [axisWidth, setAxisWidth] = useState(DEFAULT_AXIS_WIDTH)
    const [chartHeight, setChartHeight] = useState(392)
    const [isExpanded, setIsExpanded] = useState(false)
    const [isFullscreen, setIsFullscreen] = useState(false)
    const [viewportHeight, setViewportHeight] = useState<number>(() => typeof window === "undefined" ? 900 : window.innerHeight)
    const resizeRef = useRef<{ pointerId: number, startY: number, startHeight: number } | null>(null)
    const fullscreenRef = useRef<HTMLDivElement | null>(null)

    const hoveredCandle = hoverPayload?.candle
        ?? (hoverPayload?.candleIndex !== null && hoverPayload?.candleIndex !== undefined
            ? candles[hoverPayload.candleIndex] || null
            : null)
    const activeCandle = hoveredCandle || latestCandle
    // Use the live tick price (ltp) as the primary displayed price
    const latestChartClose = price ?? toNumber(latestCandle?.close) ?? 0
    const previousChartClose = candles.length > 1 ? toNumber(candles[candles.length - 2]?.close) : null
    const chartChangePct = getPercentChange(latestChartClose, previousChartClose) ?? change
    const activeTimeLabel = hoverPayload?.timeLabel || formatExactTimestamp(activeCandle?.time)
    const activeOpen = toNumber(activeCandle?.open)
    const activeHigh = toNumber(activeCandle?.high)
    const activeLow = toNumber(activeCandle?.low)
    const activeClose = toNumber(activeCandle?.close) ?? latestChartClose
    const activeVolume = activeCandle?.volume ?? volume
    const resolvedChartHeight = clamp(
        chartHeight,
        isExpanded ? 340 : MIN_CHART_HEIGHT,
        isExpanded ? MAX_CHART_HEIGHT : 430
    )
    const fullscreenChartHeight = clamp(viewportHeight - 220, 520, 1200)
    const feedAppearance = getStatusAppearance(feedStatus)
    const marketAppearance = getStatusAppearance(marketState)
    const dataModeAppearance = getStatusAppearance(dataMode)
    const surfaceTextTone = isFullscreen
        ? {
            primary: "#26344b",
            secondary: "#4d5c74",
            muted: "#5e6d86",
            hint: "#6a7890",
            accent: "#236f97",
            positive: "#287b67",
            warning: "#966614",
            negative: "#c2577b"
        }
        : {
            primary: spaceTheme.accentStrong,
            secondary: spaceTheme.textSecondary,
            muted: spaceTheme.textMuted,
            hint: spaceTheme.textMuted,
            accent: spaceTheme.accent,
            positive: spaceTheme.positive,
            warning: spaceTheme.warning,
            negative: spaceTheme.negative
        }
    const chartTrendColor = chartChangePct >= 0 ? spaceTheme.positive : spaceTheme.negative
    const trendTextTone = chartChangePct >= 0 ? surfaceTextTone.positive : surfaceTextTone.negative

    useEffect(() => {
        setHoverPayload(null)
    }, [symbol, timeframe])

    const getReadableStatusAppearance = (value: any, base: { background: string, color: string, border: string }) => {
        if (!isFullscreen) {
            return base
        }

        const normalized = String(value || "unknown").toLowerCase()

        if (["running", "live_connected", "connected", "open", "valid"].includes(normalized)) {
            return {
                ...base,
                background: "rgba(66, 190, 156, 0.12)",
                color: "#2f8c76",
                border: "1px solid rgba(66, 190, 156, 0.24)"
            }
        }

        if (["demo_fallback", "starting", "checking", "connecting", "paper", "demo", "live", "not_required"].includes(normalized)) {
            return {
                ...base,
                background: "rgba(228, 170, 67, 0.12)",
                color: "#a97016",
                border: "1px solid rgba(228, 170, 67, 0.24)"
            }
        }

        if (["error", "token_expired", "expired", "invalid", "missing", "disconnected", "stopped"].includes(normalized)) {
            return {
                ...base,
                background: "rgba(224, 101, 144, 0.12)",
                color: "#b24772",
                border: "1px solid rgba(224, 101, 144, 0.22)"
            }
        }

        return {
            ...base,
            background: "rgba(92, 119, 170, 0.10)",
            color: "#5a6881",
            border: "1px solid rgba(92, 119, 170, 0.16)"
        }
    }
    const resolvedFeedAppearance = getReadableStatusAppearance(feedStatus, feedAppearance)
    const resolvedDataModeAppearance = getReadableStatusAppearance(dataMode, dataModeAppearance)
    const resolvedMarketAppearance = getReadableStatusAppearance(marketState, marketAppearance)

    useEffect(() => {
        const handleResize = (): void => {
            setViewportHeight(window.innerHeight)
        }

        const handleFullscreenChange = (): void => {
            setIsFullscreen(document.fullscreenElement === fullscreenRef.current)
        }

        window.addEventListener("resize", handleResize)
        document.addEventListener("fullscreenchange", handleFullscreenChange)

        return () => {
            window.removeEventListener("resize", handleResize)
            document.removeEventListener("fullscreenchange", handleFullscreenChange)
        }
    }, [])

    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent): void => {
            if (event.defaultPrevented || event.repeat || event.ctrlKey || event.metaKey || event.altKey) {
                return
            }

            const target = event.target as HTMLElement | null
            const tagName = target?.tagName?.toLowerCase()
            const isEditableTarget = Boolean(
                target?.isContentEditable
                || tagName === "input"
                || tagName === "textarea"
                || tagName === "select"
            )

            if (isEditableTarget) {
                return
            }

            if (event.key.toLowerCase() === "f") {
                event.preventDefault()
                toggleFullscreen()
            }
        }

        window.addEventListener("keydown", handleKeyDown)

        return () => {
            window.removeEventListener("keydown", handleKeyDown)
        }
    }, [isFullscreen])

    const toggleFullscreen = (): void => {
        const element = fullscreenRef.current
        if (!element) {
            return
        }

        if (document.fullscreenElement === element) {
            void document.exitFullscreen?.()
            return
        }

        void element.requestFullscreen?.().catch(() => {
            setIsFullscreen(false)
        })
    }

    const chartPanel = (height: number, fullscreen: boolean): ReactElement => (
        <>
            <div
                style={{
                    ...styles.chartBox,
                    flex: "0 0 auto",
                    height,
                    minHeight: height,
                    marginBottom: fullscreen ? 0 : 8,
                    borderRadius: fullscreen ? 20 : 16,
                    padding: fullscreen ? 6 : 0
                }}
            >
                <CandleChart
                    candles={candles}
                    currentPrice={latestChartClose}
                    timeframe={timeframe}
                    loading={chartLoading}
                    error={chartError}
                    axisWidth={axisWidth}
                    onAxisWidthChange={setAxisWidth}
                    onHoverCandleChange={setHoverPayload}
                    chartHeight={height}
                    compact={!fullscreen && !isExpanded}
                />
            </div>

            {!fullscreen && (
                <div
                    style={styles.chartResizeHandle}
                    onPointerDown={(event) => {
                        resizeRef.current = {
                            pointerId: event.pointerId,
                            startY: event.clientY,
                            startHeight: resolvedChartHeight
                        }
                        event.currentTarget.setPointerCapture(event.pointerId)
                    }}
                    onPointerMove={(event) => {
                        const resizeState = resizeRef.current
                        if (!resizeState || resizeState.pointerId !== event.pointerId) {
                            return
                        }

                        setChartHeight(clamp(
                            resizeState.startHeight + (event.clientY - resizeState.startY),
                            MIN_CHART_HEIGHT,
                            MAX_CHART_HEIGHT
                        ))
                    }}
                    onPointerUp={(event) => {
                        if (resizeRef.current?.pointerId === event.pointerId) {
                            resizeRef.current = null
                            event.currentTarget.releasePointerCapture(event.pointerId)
                        }
                    }}
                    onPointerCancel={(event) => {
                        if (resizeRef.current?.pointerId === event.pointerId) {
                            resizeRef.current = null
                            event.currentTarget.releasePointerCapture(event.pointerId)
                        }
                    }}
                />
            )}
        </>
    )

    return (

        <div
            ref={fullscreenRef}
            style={{
                ...styles.container,
                ...(isFullscreen ? styles.containerFullscreen : {})
            }}
        >

            <div style={styles.header}>
                <div style={styles.headerLeft}>
                    <div style={styles.titleRow}>
                        <span style={{ ...styles.symbol, color: surfaceTextTone.primary }}>{symbol}</span>
                        <span style={{ ...styles.exchangeBadge, color: surfaceTextTone.secondary }}>{exchange}</span>
                        <span style={{ ...styles.timeframeBadge, color: surfaceTextTone.accent }}>{timeframeLabel}</span>
                        <span style={{ ...styles.sourceBadge, color: surfaceTextTone.positive }}>{chartSource === "historical_api" ? "History" : "Stream"}</span>
                        <button
                            style={styles.chartActionButton}
                            onClick={() => {
                                setIsExpanded((current) => {
                                    const next = !current
                                    setChartHeight((existingHeight) => next
                                        ? Math.max(existingHeight, 454)
                                        : Math.max(MIN_CHART_HEIGHT, Math.min(existingHeight, 320)))
                                    return next
                                })
                            }}
                        >
                            {isExpanded ? "Minimize" : "Maximize"}
                        </button>
                        <button
                            style={styles.chartActionButton}
                            onClick={toggleFullscreen}
                        >
                            {isFullscreen ? "F Exit Fullscreen" : "F Fullscreen"}
                        </button>
                    </div>

                    <div style={{ ...styles.ohlcRow, color: surfaceTextTone.muted }}>
                        <span>O {formatPrice(activeOpen)}</span>
                        <span>H {formatPrice(activeHigh)}</span>
                        <span>L {formatPrice(activeLow)}</span>
                        <span>C {formatPrice(activeClose)}</span>
                        <span>V {formatVolume(activeVolume)}</span>
                        {activeTimeLabel && <span>{activeTimeLabel}</span>}
                    </div>
                </div>

                <div style={styles.headerRight}>
                    <span style={{ ...styles.price, color: isFullscreen ? trendTextTone : chartTrendColor }}>
                        {formatPrice(latestChartClose)}
                    </span>
                    <span style={{ ...styles.changeText, color: isFullscreen ? trendTextTone : chartTrendColor }}>
                        {formatChange(chartChangePct)}
                    </span>
                </div>
            </div>

            <div style={styles.toolbar}>
                <div style={styles.intervalBar}>
                    {INTERVAL_OPTIONS.map((option) => {
                        const isActive = timeframe === option.value
                        return (
                            <button
                                key={option.value}
                                style={isActive ? styles.intervalButtonActive : styles.intervalButton}
                                onClick={() => data?.onTimeframeChange?.(option.value)}
                            >
                                {option.label}
                            </button>
                        )
                    })}
                </div>

                <div style={styles.statusRow}>
                    <span style={{ ...styles.statusPill, ...resolvedFeedAppearance }}>
                        {formatStatusLabel(feedStatus)}
                    </span>
                    <span style={{ ...styles.statusPill, ...resolvedDataModeAppearance }}>
                        {formatStatusLabel(dataMode)}
                    </span>
                    <span style={{ ...styles.statusPill, ...resolvedMarketAppearance }}>
                        {formatStatusLabel(marketState)}
                    </span>
                    <span style={{ ...styles.panHint, color: surfaceTextTone.hint }}>Hover crosshair • drag to pan • wheel to zoom • double-click reset • drag scale edge to widen prices</span>
                    {chartError && <span style={{ ...styles.warningText, color: surfaceTextTone.warning }}>{chartError}</span>}
                </div>
            </div>

            {chartPanel(isFullscreen ? fullscreenChartHeight : resolvedChartHeight, isFullscreen)}

            <div style={{ ...styles.footer, color: surfaceTextTone.muted }}>
                <span>Bid: {formatPrice(bid)}</span>
                <span>Ask: {formatPrice(ask)}</span>
                <span>Volume: {formatVolume(volume)}</span>
            </div>

        </div>
    )
}

export default LiveMarketPanel


const styles: any = {

    container: {
        height: "100%",
        display: "flex",
        flexDirection: "column",
        ...panelShell,
        padding: 14,
        borderRadius: 18,
        minHeight: 0
    },

    containerFullscreen: {
        width: "100%",
        height: "100%",
        padding: 20,
        borderRadius: 0,
        background: chartTheme.background,
        border: "none",
        boxShadow: "none"
    },

    header: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: 14,
        marginBottom: 12
    },

    headerLeft: {
        display: "flex",
        flexDirection: "column",
        gap: 8
    },

    titleRow: {
        display: "flex",
        alignItems: "center",
        gap: 10,
        flexWrap: "wrap"
    },

    symbol: {
        fontSize: 26,
        fontWeight: 700,
        color: spaceTheme.accentStrong,
        letterSpacing: "0.06em",
        fontFamily: spaceTheme.titleFamily,
        textTransform: "uppercase"
    },

    exchangeBadge: {
        padding: "5px 10px",
        borderRadius: 999,
        background: "rgba(140, 216, 255, 0.12)",
        color: spaceTheme.textSecondary,
        fontSize: 12,
        fontWeight: 700,
        border: "1px solid rgba(140, 216, 255, 0.14)"
    },

    timeframeBadge: {
        padding: "5px 10px",
        borderRadius: 999,
        background: "rgba(112, 194, 255, 0.14)",
        color: spaceTheme.accent,
        fontSize: 12,
        fontWeight: 700,
        border: "1px solid rgba(112, 194, 255, 0.14)"
    },

    sourceBadge: {
        padding: "5px 10px",
        borderRadius: 999,
        background: "rgba(114, 255, 210, 0.12)",
        color: spaceTheme.positive,
        fontSize: 12,
        fontWeight: 700,
        border: "1px solid rgba(114, 255, 210, 0.14)"
    },

    ohlcRow: {
        display: "flex",
        gap: 14,
        color: spaceTheme.textMuted,
        fontSize: 13,
        flexWrap: "wrap"
    },

    chartActionButton: {
        background: "linear-gradient(180deg, rgba(13, 34, 58, 0.96) 0%, rgba(8, 19, 35, 0.98) 100%)",
        border: "1px solid rgba(135, 216, 255, 0.16)",
        color: spaceTheme.accentStrong,
        borderRadius: 10,
        cursor: "pointer",
        padding: "7px 10px",
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: "0.04em"
    },

    headerRight: {
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-end",
        gap: 4
    },

    price: {
        fontSize: 30,
        fontWeight: 700
    },

    changeText: {
        fontSize: 16,
        fontWeight: 700
    },

    toolbar: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
        marginBottom: 12,
        flexWrap: "wrap"
    },

    intervalBar: {
        display: "flex",
        gap: 8,
        flexWrap: "wrap"
    },

    intervalButton: {
        background: "linear-gradient(180deg, rgba(9, 23, 40, 0.9) 0%, rgba(5, 13, 24, 0.96) 100%)",
        border: "1px solid rgba(129, 206, 255, 0.16)",
        color: spaceTheme.textMuted,
        padding: "8px 12px",
        borderRadius: 10,
        cursor: "pointer",
        fontSize: 12,
        fontWeight: 700,
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.04)"
    },

    intervalButtonActive: {
        background: "linear-gradient(180deg, rgba(165, 239, 255, 0.94) 0%, rgba(109, 209, 255, 0.92) 100%)",
        border: "1px solid rgba(216, 249, 255, 0.95)",
        color: "#06111f",
        padding: "8px 12px",
        borderRadius: 10,
        cursor: "pointer",
        fontSize: 12,
        fontWeight: 700,
        boxShadow: "0 0 18px rgba(147, 233, 255, 0.24)"
    },

    statusRow: {
        display: "flex",
        alignItems: "center",
        gap: 10,
        flexWrap: "wrap"
    },

    statusPill: {
        padding: "6px 10px",
        borderRadius: 999,
        background: "rgba(145, 238, 255, 0.12)",
        color: spaceTheme.accent,
        fontSize: 12,
        fontWeight: 700,
        border: "1px solid rgba(145, 238, 255, 0.12)"
    },

    panHint: {
        color: "#7b89a2",
        fontSize: 12
    },

    warningText: {
        color: "#a97016",
        fontSize: 12
    },

    chartBox: {
        ...innerShell,
        background: chartTheme.background,
        border: "1px solid rgba(255,255,255,0.05)",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.03), 0 18px 32px rgba(0,0,0,0.26)",
        borderRadius: 16,
        overflow: "hidden",
        position: "relative",
        marginBottom: 12,
        minHeight: 340,
        width: "100%"
    },

    chartViewport: {
        width: "100%",
        height: "100%",
        position: "relative",
        display: "flex",
        minHeight: 0
    },

    plotSurface: {
        flex: 1,
        minWidth: 0,
        height: "100%",
        position: "relative",
        touchAction: "none",
        cursor: "crosshair"
    },

    candleSvg: {
        width: "100%",
        height: "100%",
        display: "block",
        background: chartTheme.background
    },

    rightAxis: {
        position: "relative",
        background: chartTheme.axisPanel,
        borderLeft: `1px solid ${chartTheme.axisBorder}`,
        overflow: "hidden"
    },

    axisResizeHandle: {
        position: "absolute",
        top: 0,
        bottom: 0,
        left: 0,
        width: 10,
        cursor: "ew-resize",
        zIndex: 2,
        background: "linear-gradient(180deg, rgba(148, 163, 184, 0.1) 0%, rgba(148, 163, 184, 0) 100%)"
    },

    axisLabel: {
        position: "absolute",
        right: 8,
        color: chartTheme.axisText,
        fontSize: 11,
        fontVariantNumeric: "tabular-nums",
        whiteSpace: "nowrap"
    },

    hoverPricePill: {
        position: "absolute",
        right: 6,
        padding: "3px 7px",
        borderRadius: 8,
        background: "rgba(2, 6, 23, 0.94)",
        border: "1px solid rgba(56, 189, 248, 0.36)",
        color: chartTheme.axisText,
        fontSize: 11,
        fontWeight: 700,
        boxShadow: "0 0 12px rgba(2, 6, 23, 0.3)"
    },

    currentPricePill: {
        position: "absolute",
        right: 6,
        padding: "3px 7px",
        borderRadius: 8,
        background: chartTheme.priceLine,
        color: "#082032",
        fontSize: 11,
        fontWeight: 700,
        boxShadow: `0 0 16px ${chartTheme.currentPriceGlow}`
    },

    chartOverlay: {
        position: "absolute",
        top: 12,
        left: 12,
        padding: "6px 10px",
        borderRadius: 10,
        background: "rgba(2, 6, 23, 0.86)",
        border: "1px solid rgba(255,255,255,0.05)",
        color: chartTheme.axisText,
        fontSize: 12
    },

    chartResizeHandle: {
        height: 12,
        marginBottom: 10,
        borderRadius: 999,
        border: "1px solid rgba(123, 210, 255, 0.12)",
        background: "linear-gradient(90deg, rgba(41, 208, 109, 0.82) 0%, rgba(74, 224, 255, 0.82) 50%, rgba(41, 208, 109, 0.82) 100%)",
        boxShadow: "0 0 18px rgba(52, 220, 171, 0.16)",
        cursor: "ns-resize",
        flexShrink: 0
    },

    emptyChart: {
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: spaceTheme.textMuted,
        fontSize: 13,
        letterSpacing: "0.02em"
    },

    footer: {
        display: "flex",
        justifyContent: "space-between",
        fontSize: 13,
        color: "#6d7b94",
        flexWrap: "wrap",
        gap: 10
    }

}
