import React, { useEffect, useState, ReactElement, startTransition, useRef } from "react"
import {
    apiService,
    SymbolSearchResult,
    OptionChainResponse
} from "./api_service"
import { panelShell, spaceTheme } from "./theme"

import LiveMarketPanel from "./live_market_panel"
import AISignalPanel, { TradeSignal } from "./ai_signal_panel"
import PnlCurveChart from "./pnl_curve_chart"
import StrategyControlPanel from "./strategy_control_panel"
import AnalyticsDashboard from "./analytics_dashboard"
import SystemHealthWidget from "./system_health_widget"
import OptionChainHeatmap from "./option_chain_heatmap"
import GreeksPanel from "./greeks_panel"
import OrderPanel from "./order_panel"
import PositionPanel from "./position_panel"

type ChartInterval = "minute" | "5minute" | "15minute" | "60minute" | "day"

type Candle = {
    time?: string
    open?: number
    high?: number
    low?: number
    close?: number
    volume?: number
}

const INTERVAL_CONFIG: Record<ChartInterval, { label: string, days: number, limit: number }> = {
    minute: { label: "1m", days: 2, limit: 360 },
    "5minute": { label: "5m", days: 5, limit: 320 },
    "15minute": { label: "15m", days: 20, limit: 320 },
    "60minute": { label: "1h", days: 60, limit: 320 },
    day: { label: "1D", days: 220, limit: 320 }
}

const normalizeCandle = (candle: any): Candle => ({
    time: candle?.time,
    open: candle?.open,
    high: candle?.high,
    low: candle?.low,
    close: candle?.close,
    volume: candle?.volume ?? 0
})

const toFiniteNumber = (value: any): number | null => {
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

const toTimestamp = (value: string | undefined): number | null => {
    const parsed = parseChartDate(value)
    const timestamp = parsed ? parsed.getTime() : null
    return Number.isFinite(timestamp) ? timestamp : null
}

const sortCandles = (candles: Candle[]): Candle[] => {
    return [...candles].sort((left, right) => {
        const leftTime = parseChartDate(left.time)?.getTime() ?? 0
        const rightTime = parseChartDate(right.time)?.getTime() ?? 0
        return leftTime - rightTime
    })
}

const getCandleMergeKey = (candle: Candle, fallbackIndex: number): string => {
    const timestamp = toTimestamp(candle.time)
    return timestamp !== null ? String(timestamp) : `candle-${fallbackIndex}`
}

const getChartCacheKey = (symbol: string, exchange: string, interval: ChartInterval): string => {
    return `${normalizeSearchText(exchange)}:${normalizeSearchText(symbol)}:${interval}`
}

const aggregateLiveCandles = (candles: Candle[], interval: ChartInterval): Candle[] => {
    const bucketMs =
        interval === "60minute" ? 60 * 60 * 1000 :
        interval === "15minute" ? 15 * 60 * 1000 :
        interval === "5minute" ? 5 * 60 * 1000 :
        interval === "minute" ? 60 * 1000 :
        0

    if (!bucketMs) {
        return []
    }

    const aggregatedByBucket = new Map<string, Candle>()

    sortCandles(candles).forEach((rawCandle) => {
        const candle = normalizeCandle(rawCandle)
        const timestamp = toTimestamp(candle.time)

        if (timestamp === null) {
            return
        }

        const bucketStart = timestamp - (timestamp % bucketMs)
        const key = new Date(bucketStart).toISOString()
        const open = toFiniteNumber(candle.open)
        const high = toFiniteNumber(candle.high)
        const low = toFiniteNumber(candle.low)
        const close = toFiniteNumber(candle.close)
        const volume = toFiniteNumber(candle.volume) ?? 0

        if (open === null || high === null || low === null || close === null) {
            return
        }

        const existing = aggregatedByBucket.get(key)
        if (!existing) {
            aggregatedByBucket.set(key, {
                time: key,
                open,
                high,
                low,
                close,
                volume
            })
            return
        }

        aggregatedByBucket.set(key, {
            time: key,
            open: existing.open,
            high: Math.max(toFiniteNumber(existing.high) ?? high, high),
            low: Math.min(toFiniteNumber(existing.low) ?? low, low),
            close,
            volume: (toFiniteNumber(existing.volume) ?? 0) + volume
        })
    })

    return sortCandles(Array.from(aggregatedByBucket.values()))
}

const mergeCandles = (historicalCandles: Candle[], liveCandles: Candle[], interval: ChartInterval): Candle[] => {
    const safeHistorical = Array.isArray(historicalCandles) ? historicalCandles.map(normalizeCandle) : []
    const safeLive = Array.isArray(liveCandles) ? liveCandles.map(normalizeCandle) : []
    
    // Don't merge live candles for daily timeframe - historical data is complete
    if (interval === "day") {
        return sortCandles(safeHistorical).slice(-INTERVAL_CONFIG[interval].limit)
    }
    
    // Get the last historical candle timestamp to check for overnight gaps
    const sortedHistorical = sortCandles(safeHistorical)
    const lastHistoricalTime = sortedHistorical.length > 0 
        ? toTimestamp(sortedHistorical[sortedHistorical.length - 1].time)
        : null
    
    // Market trading hours: 9:15 AM to 3:30 PM IST
    const MARKET_OPEN_MINUTES = 555   // 9:15 AM = 9*60 + 15
    const MARKET_CLOSE_MINUTES = 930  // 3:30 PM = 15*60 + 30
    
    // Check if a timestamp is within market hours
    const isWithinMarketHours = (timestamp: number): boolean => {
        const date = new Date(timestamp)
        // Convert to IST (UTC+5:30)
        const utcHours = date.getUTCHours()
        const utcMinutes = date.getUTCMinutes()
        const istMinutes = (utcHours * 60 + utcMinutes) + 330  // Add 5.5 hours
        const normalizedMinutes = istMinutes % 1440  // Handle day overflow
        return normalizedMinutes >= MARKET_OPEN_MINUTES && normalizedMinutes <= MARKET_CLOSE_MINUTES
    }
    
    // Filter live candles to only include those from current trading session
    const filteredLive = safeLive.filter((candle) => {
        const liveTime = toTimestamp(candle.time)
        if (liveTime === null) {
            return false
        }
        
        // Only include candles from within market hours
        if (!isWithinMarketHours(liveTime)) {
            return false
        }
        
        // If we have historical data, only include candles that are on the same day or after
        if (lastHistoricalTime !== null) {
            const lastHistDate = new Date(lastHistoricalTime)
            const liveDate = new Date(liveTime)
            
            // Get dates in IST
            const lastHistDay = new Date(lastHistDate.getTime() + 330 * 60 * 1000).toDateString()
            const liveDay = new Date(liveDate.getTime() + 330 * 60 * 1000).toDateString()
            
            // If live candle is from a different day, it's a new session
            // Only add it as a new candle, don't try to merge
            if (lastHistDay !== liveDay) {
                return true  // Allow but will be handled as new candle
            }
        }
        
        return true
    })
    
    const liveForInterval = interval === "minute"
        ? sortCandles(filteredLive)
        : aggregateLiveCandles(filteredLive, interval)

    const mergedByTime = new Map<string, Candle>()

    sortedHistorical.forEach((candle) => {
        const key = getCandleMergeKey(candle, mergedByTime.size)
        mergedByTime.set(key, candle)
    })

    // Only merge live candles that fall within same time bucket as historical
    liveForInterval.forEach((liveCandle) => {
        const key = getCandleMergeKey(liveCandle, mergedByTime.size)
        const existing = mergedByTime.get(key)

        if (!existing) {
            // New candle - add only if it's within market hours and after last historical
            const liveTime = toTimestamp(liveCandle.time)
            if (liveTime !== null && isWithinMarketHours(liveTime)) {
                // For new session candles, use the live candle's OHLC as-is
                mergedByTime.set(key, liveCandle)
            }
            return
        }

        // Existing bucket - update only high, low, close (preserve original open)
        mergedByTime.set(key, {
            time: existing.time || liveCandle.time,
            open: existing.open,  // Keep historical open, don't override
            high: Math.max(
                toFiniteNumber(existing.high) ?? Number.NEGATIVE_INFINITY,
                toFiniteNumber(liveCandle.high) ?? Number.NEGATIVE_INFINITY
            ),
            low: Math.min(
                toFiniteNumber(existing.low) ?? Number.POSITIVE_INFINITY,
                toFiniteNumber(liveCandle.low) ?? Number.POSITIVE_INFINITY
            ),
            close: toFiniteNumber(liveCandle.close) ?? existing.close,
            volume: (toFiniteNumber(liveCandle.volume) ?? 0) > 0
                ? liveCandle.volume
                : existing.volume
        })
    })

    return sortCandles(Array.from(mergedByTime.values())).slice(-INTERVAL_CONFIG[interval].limit)
}

const getFallbackPrice = (candles: Candle[]): number => {
    const lastCandle = candles[candles.length - 1]
    return typeof lastCandle?.close === "number" ? lastCandle.close : 0
}

const getFallbackChangePct = (candles: Candle[]): number => {
    if (candles.length < 2) {
        return 0
    }

    const previousClose = candles[candles.length - 2]?.close
    const latestClose = candles[candles.length - 1]?.close

    if (typeof previousClose !== "number" || typeof latestClose !== "number" || previousClose === 0) {
        return 0
    }

    return ((latestClose - previousClose) / previousClose) * 100
}

const normalizeSearchText = (value: string | undefined | null): string => {
    return (value || "").trim().toUpperCase()
}

const findBestSearchMatch = (
    query: string,
    results: SymbolSearchResult[],
    exactOnly: boolean = false
): SymbolSearchResult | null => {
    const normalizedQuery = normalizeSearchText(query)

    if (!normalizedQuery || results.length === 0) {
        return null
    }

    const exactMatch = results.find((result) => {
        return [
            result.symbol,
            result.tradingsymbol,
            result.name
        ].some((value) => normalizeSearchText(value) === normalizedQuery)
    })

    if (exactMatch) {
        return exactMatch
    }

    if (exactOnly) {
        return null
    }

    const prefixMatch = results.find((result) => {
        return [
            result.symbol,
            result.tradingsymbol,
            result.name
        ].some((value) => normalizeSearchText(value).startsWith(normalizedQuery))
    })

    if (prefixMatch) {
        return prefixMatch
    }

    if (results.length === 1) {
        return results[0]
    }

    return results[0] || null
}

const SymbolSearchBar = ({
    query,
    selectedSymbol,
    selectedExchange,
    results,
    loading,
    error,
    onQueryChange,
    onSelect,
    onSubmit
}: {
    query: string
    selectedSymbol: string
    selectedExchange: string
    results: SymbolSearchResult[]
    loading: boolean
    error: string
    onQueryChange: (value: string) => void
    onSelect: (result: SymbolSearchResult) => void
    onSubmit: () => void
}): ReactElement => {
    const [isFocused, setIsFocused] = useState(false)
    const blurTimerRef = useRef<number | undefined>(undefined)
    const normalizedQuery = query.trim().toUpperCase()
    const hasResults = results.length > 0
    const showDropdown = isFocused && Boolean(normalizedQuery) && (
        loading
        || Boolean(error)
        || hasResults
        || normalizedQuery !== selectedSymbol.toUpperCase()
    )

    return (
        <div style={styles.searchContainer}>
            <div style={styles.searchShell}>
                <span style={styles.searchIcon}>Search</span>
                <input
                    value={query}
                    onChange={(event) => onQueryChange(event.target.value)}
                    onKeyDown={(event) => {
                        if (event.key === "Enter") {
                            event.preventDefault()
                            onSubmit()
                        }
                    }}
                    onFocus={() => {
                        if (blurTimerRef.current) {
                            window.clearTimeout(blurTimerRef.current)
                        }
                        setIsFocused(true)
                    }}
                    onBlur={() => {
                        blurTimerRef.current = window.setTimeout(() => {
                            setIsFocused(false)
                        }, 140)
                    }}
                    placeholder="Search indices or stocks"
                    style={styles.searchInput}
                />
                <button
                    type="button"
                    style={styles.searchApplyButton}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={onSubmit}
                >
                    Go
                </button>
            </div>

            {showDropdown && (
                <div style={styles.searchDropdown}>
                    {loading && <div style={styles.searchState}>Searching...</div>}
                    {!loading && error && <div style={styles.searchState}>{error}</div>}
                    {!loading && !error && results.length === 0 && query.trim() && (
                        <div style={styles.searchState}>No matching symbols found.</div>
                    )}
                    {!loading && !error && results.map((result) => (
                        <button
                            key={`${result.exchange}-${result.symbol}`}
                            style={result.symbol === selectedSymbol && result.exchange === selectedExchange ? styles.searchItemActive : styles.searchItem}
                            onMouseDown={(event) => {
                                event.preventDefault()
                                if (blurTimerRef.current) {
                                    window.clearTimeout(blurTimerRef.current)
                                }
                                setIsFocused(false)
                                onSelect(result)
                            }}
                            title={`${result.exchange} ${result.symbol} ${result.last_price ?? "--"}`}
                        >
                            <div style={styles.searchRow}>
                                <span style={styles.searchSymbol}>{result.symbol}</span>
                                <span style={styles.searchPrice}>
                                    {typeof result.last_price === "number"
                                        ? result.last_price.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                                        : "--"}
                                </span>
                            </div>
                            <span style={styles.searchMeta}>{result.name || result.tradingsymbol} · {result.exchange}</span>
                        </button>
                    ))}
                </div>
            )}
        </div>
    )
}

const MainDashboard = (): ReactElement => {

    const [streamState, setStreamState] = useState<any>({
        market: {},
        signal: {},
        pnl: {},
        system: {},
        candles: {},
        greeks: {}
    })
    const [selectedSymbol, setSelectedSymbol] = useState<string>("NIFTY")
    const [selectedExchange, setSelectedExchange] = useState<string>("NSE")
    const [selectedInstrument, setSelectedInstrument] = useState<SymbolSearchResult | null>(null)
    const [selectedInterval, setSelectedInterval] = useState<ChartInterval>("day")
    const [historicalCandles, setHistoricalCandles] = useState<Candle[]>([])
    const [chartSource, setChartSource] = useState<string>("")
    const [chartLoading, setChartLoading] = useState<boolean>(false)
    const [chartError, setChartError] = useState<string>("")
    const [searchQuery, setSearchQuery] = useState<string>("NIFTY")
    const [searchResults, setSearchResults] = useState<SymbolSearchResult[]>([])
    const [searchLoading, setSearchLoading] = useState<boolean>(false)
    const [searchError, setSearchError] = useState<string>("")
    const [watchError, setWatchError] = useState<string>("")
    const [optionChain, setOptionChain] = useState<OptionChainResponse>({
        type: "option_chain",
        symbol: "NIFTY",
        strikes: []
    })
    const [optionChainLoading, setOptionChainLoading] = useState<boolean>(false)
    const [optionChainError, setOptionChainError] = useState<string>("")
    const [showOrderPanel, setShowOrderPanel] = useState<boolean>(false)
    const [prefilledTrade, setPrefilledTrade] = useState<TradeSignal | null>(null)
    const optionChainRequestInFlight = useRef(false)
    const chartHistoryCacheRef = useRef<Record<string, Candle[]>>({})
    
    // Handle "Take Trade" from signal panel - opens order panel with prefilled data
    const handleTakeTrade = (signal: TradeSignal) => {
        setPrefilledTrade(signal)
        setShowOrderPanel(true)
    }
    const applySearchSelection = (result: SymbolSearchResult): void => {
        const nextSymbol = normalizeSearchText(result.symbol || result.tradingsymbol || searchQuery)
        const nextExchange = normalizeSearchText(result.exchange || "NSE") || "NSE"

        startTransition(() => {
            const nextChartCacheKey = getChartCacheKey(nextSymbol, nextExchange, selectedInterval)
            setSelectedSymbol(nextSymbol)
            setSelectedExchange(nextExchange)
            setSelectedInstrument(result)
            setSearchQuery(nextSymbol)
            setSearchResults([])
            setSearchError("")
            setWatchError("")
            setChartError("")
            setChartSource("")
            setHistoricalCandles(chartHistoryCacheRef.current[nextChartCacheKey] ?? [])
            setOptionChain({
                type: "option_chain",
                symbol: nextSymbol,
                strikes: []
            })
            setOptionChainError("")
        })
    }

    const submitSearchSelection = (): void => {
        const match = findBestSearchMatch(searchQuery, searchResults)
        if (match) {
            applySearchSelection(match)
            return
        }

        const normalizedQuery = normalizeSearchText(searchQuery)
        if (!normalizedQuery) {
            return
        }

        setSearchError("No matching symbol to apply yet. Pick a result or press Enter after the search list appears.")
    }

    useEffect(() => {

        apiService.subscribe((state: any) => {
            console.log("📊 Dashboard received state update:", state)
            startTransition(() => {
                setStreamState({ ...state })
            })
        })

    }, [])

    useEffect(() => {
        let cancelled = false
        let refreshTimer: number | undefined

        const runSearch = async (showLoader: boolean): Promise<void> => {
            const query = searchQuery.trim()

            if (!query) {
                startTransition(() => {
                    setSearchResults([])
                    setSearchError("")
                    setSearchLoading(false)
                })
                return
            }

            if (showLoader) {
                setSearchLoading(true)
            }
            setSearchError("")

            try {
                const response = await apiService.searchSymbols(query, 16, ["NSE", "BSE"])
                if (cancelled) {
                    return
                }

                startTransition(() => {
                    setSearchResults(response.results || [])
                })
            } catch (error) {
                if (cancelled) {
                    return
                }

                const message = error instanceof Error ? error.message : "Unable to search symbols"
                startTransition(() => {
                    setSearchResults([])
                    setSearchError(message)
                })
            } finally {
                if (!cancelled && showLoader) {
                    setSearchLoading(false)
                }
            }
        }

        const debounceTimer = window.setTimeout(() => {
            void runSearch(true)
            if (searchQuery.trim()) {
                refreshTimer = window.setInterval(() => {
                    void runSearch(false)
                }, 5000)
            }
        }, 220)

        return () => {
            cancelled = true
            window.clearTimeout(debounceTimer)
            if (refreshTimer) {
                window.clearInterval(refreshTimer)
            }
        }
    }, [searchQuery])

    useEffect(() => {
        let cancelled = false

        const ensureLiveWatch = async (): Promise<void> => {
            setWatchError("")

            try {
                const response = await apiService.watchSymbol(
                    selectedSymbol,
                    selectedExchange
                )

                if (cancelled) {
                    return
                }

                if (response?.status === "subscribed") {
                    const resolvedSymbol = normalizeSearchText(response.symbol || selectedSymbol)
                    const resolvedExchange = normalizeSearchText(response.exchange || selectedExchange) || "NSE"

                    if (resolvedSymbol !== normalizeSearchText(selectedSymbol)) {
                        startTransition(() => {
                            setSelectedSymbol(resolvedSymbol)
                            setSearchQuery(resolvedSymbol)
                        })
                    }

                    if (resolvedExchange !== normalizeSearchText(selectedExchange)) {
                        startTransition(() => {
                            setSelectedExchange(resolvedExchange)
                        })
                    }
                }
            } catch (error) {
                if (cancelled) {
                    return
                }

                const message = error instanceof Error ? error.message : "Unable to subscribe live symbol"
                startTransition(() => {
                    setWatchError(message)
                })
            }
        }

        ensureLiveWatch()

        return () => {
            cancelled = true
        }
    }, [selectedExchange, selectedInstrument, selectedSymbol])

    const system = streamState.system || {}
    const market = streamState.market || {}
    const streamCandles = streamState.candles || {}
    const selectedTick = market?.[selectedSymbol] || {}
    const rawCandleSeries = streamCandles?.[selectedSymbol]
    const liveCandleSeries = Array.isArray(rawCandleSeries) ? rawCandleSeries : []
    const selectedIntervalConfig = INTERVAL_CONFIG[selectedInterval]

    useEffect(() => {
        let cancelled = false
        const chartCacheKey = getChartCacheKey(selectedSymbol, selectedExchange, selectedInterval)

        const loadChartHistory = async (): Promise<void> => {
            setChartLoading(true)
            setChartError("")
            if (chartHistoryCacheRef.current[chartCacheKey]?.length) {
                setHistoricalCandles(chartHistoryCacheRef.current[chartCacheKey])
                setChartSource("cache")
            } else {
                setChartSource("")
            }

            try {
                const response = await apiService.fetchChartHistory(
                    selectedSymbol,
                    selectedInterval,
                    selectedIntervalConfig.days,
                    selectedIntervalConfig.limit,
                    selectedExchange
                )

                if (cancelled) {
                    return
                }

                startTransition(() => {
                    const normalizedCandles = Array.isArray(response.candles) ? response.candles.map(normalizeCandle) : []
                    if (normalizedCandles.length > 0) {
                        chartHistoryCacheRef.current[chartCacheKey] = normalizedCandles
                        setHistoricalCandles(normalizedCandles)
                        setChartSource(response.source || "unknown")
                    } else {
                        const cachedCandles = chartHistoryCacheRef.current[chartCacheKey]
                        if (cachedCandles?.length) {
                            setHistoricalCandles(cachedCandles)
                            setChartSource("cache")
                        } else {
                            setHistoricalCandles([])
                            setChartSource("stream")
                        }
                    }
                    setChartError(response.error || "")
                })
            } catch (error) {
                if (cancelled) {
                    return
                }

                const message = error instanceof Error ? error.message : "Unable to load chart history"

                startTransition(() => {
                    const cachedCandles = chartHistoryCacheRef.current[chartCacheKey]
                    if (cachedCandles?.length) {
                        setHistoricalCandles(cachedCandles)
                        setChartSource("cache")
                    } else {
                        setChartSource("stream")
                    }
                    setChartError(message)
                })
            } finally {
                if (!cancelled) {
                    setChartLoading(false)
                }
            }
        }

        if (selectedSymbol) {
            loadChartHistory()
        }

        return () => {
            cancelled = true
        }
    }, [selectedExchange, selectedInterval, selectedIntervalConfig.days, selectedIntervalConfig.limit, selectedSymbol])

    useEffect(() => {
        let cancelled = false
        let timer: number | undefined

        const loadOptionChain = async (showInitialLoader: boolean): Promise<void> => {
            if (optionChainRequestInFlight.current) {
                return
            }

            optionChainRequestInFlight.current = true

            if (showInitialLoader) {
                setOptionChainLoading(true)
                setOptionChain({
                    type: "option_chain",
                    symbol: selectedSymbol,
                    strikes: []
                })
            }
            setOptionChainError("")

            try {
                const response = await apiService.fetchOptionChain(selectedSymbol, 18, selectedExchange)
                if (cancelled) {
                    return
                }

                startTransition(() => {
                    setOptionChain(response)
                })
            } catch (error) {
                if (cancelled) {
                    return
                }

                const message = error instanceof Error ? error.message : "Unable to load option chain"
                startTransition(() => {
                    setOptionChain({
                        type: "option_chain",
                        symbol: selectedSymbol,
                        strikes: []
                    })
                    setOptionChainError(message)
                })
            } finally {
                optionChainRequestInFlight.current = false
                if (!cancelled) {
                    if (showInitialLoader) {
                        setOptionChainLoading(false)
                    }
                }
            }
        }

        loadOptionChain(true)
        timer = window.setInterval(() => {
            void loadOptionChain(false)
        }, 1000)

        return () => {
            cancelled = true
            if (timer) {
                window.clearInterval(timer)
            }
        }
    }, [selectedExchange, selectedSymbol])

    const normalizedMarketState = String(system?.market_state || "").toLowerCase()
    const isMarketOpen = normalizedMarketState === "open"
    
    // Only merge live candles when market is OPEN (not pre_open or closed)
    const canUseLiveOverlay = isMarketOpen
        && liveCandleSeries.length > 0
        && selectedInterval !== "day"
    const chartCandles = mergeCandles(
        historicalCandles,
        canUseLiveOverlay ? liveCandleSeries : [],
        selectedInterval
    )
    const hasLiveOverlay = canUseLiveOverlay
    const fallbackPrice = getFallbackPrice(chartCandles)
    const fallbackChangePct = getFallbackChangePct(chartCandles)
    
    // Live tick price for header ticker (shows pre-open prices)
    const liveTickPrice = selectedTick.price ?? selectedTick.ltp ?? fallbackPrice ?? 0
    
    // Chart price: Use yesterday's close during pre_open/closed, live only when market is OPEN
    const chartPrice = isMarketOpen ? liveTickPrice : fallbackPrice

    const liveData = {
        symbol: selectedSymbol,
        exchange: selectedExchange,
        ltp: chartPrice,  // Chart uses historical close during pre-open
        change_pct: fallbackChangePct,
        bid: selectedTick.bid ?? 0,
        ask: selectedTick.ask ?? 0,
        volume: selectedTick.volume ?? 0,
        candles: chartCandles,
        timeframe: selectedInterval,
        timeframeLabel: selectedIntervalConfig.label,
        chartLoading,
        chartError: chartError || watchError,
        chartSource: hasLiveOverlay ? "stream" : chartSource,
        system,
        onTimeframeChange: setSelectedInterval
    }

    const signalBySymbol = streamState.signalBySymbol || {}
    const greeksBySymbol = streamState.greeksBySymbol || {}
    const analyticsBySymbol = streamState.analyticsBySymbol || {}

    const selectedSignal = signalBySymbol[selectedSymbol]
        || (streamState.signal?.symbol === selectedSymbol ? streamState.signal : {})
    const selectedGreeks = greeksBySymbol[selectedSymbol]
        || (streamState.greeks?.symbol === selectedSymbol ? streamState.greeks : {})
    const selectedAnalytics = analyticsBySymbol[selectedSymbol]
        || (streamState.analytics?.symbol === selectedSymbol ? streamState.analytics : {})

    const analyticsData = {
        symbol: selectedAnalytics?.symbol || selectedSymbol,
        regime: selectedAnalytics?.regime || "Neutral",
        volatility: selectedAnalytics?.volatility || 0,
        momentum: selectedAnalytics?.momentum || 0
    }

    const optionChainData = {
        ...optionChain,
        symbol: selectedSymbol,
        loading: optionChainLoading,
        error: optionChainError
    }

    return (

        <div style={styles.container}>
            <div style={styles.backdrop} />
            <div style={styles.starfield} />
            <div style={styles.galaxyHalo} />
            <div style={styles.galaxyCore} />
            <div style={styles.galaxyDust} />

            <div style={styles.content}>

                <div style={styles.header}>
                    <div style={styles.headerTitle}>
                        <h2 style={styles.title}>AI Algo Trading Dashboard</h2>
                        <span style={styles.subtitle}>
                            Live Market Data • {system?.data_mode === "live" ? "🟢 LIVE" : "🟡 " + (system?.data_mode || "connecting")}
                            {!isMarketOpen && " • Market: " + (normalizedMarketState || "checking")}
                        </span>
                    </div>

                    {/* Live Price Ticker - Shows pre-open prices in header */}
                    <div style={styles.liveTicker}>
                        <div style={styles.tickerSymbol}>{selectedSymbol}</div>
                        <div style={{
                            ...styles.tickerPrice,
                            color: (selectedTick.change_pct ?? fallbackChangePct) >= 0 ? "#00e676" : "#ff5252"
                        }}>
                            {liveTickPrice.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div style={{
                            ...styles.tickerChange,
                            color: (selectedTick.change_pct ?? fallbackChangePct) >= 0 ? "#00e676" : "#ff5252",
                            background: (selectedTick.change_pct ?? fallbackChangePct) >= 0 ? "rgba(0, 230, 118, 0.15)" : "rgba(255, 82, 82, 0.15)"
                        }}>
                            {(selectedTick.change_pct ?? fallbackChangePct) >= 0 ? "▲" : "▼"} {Math.abs(selectedTick.change_pct ?? fallbackChangePct).toFixed(2)}%
                        </div>
                        <div style={styles.tickerMeta}>
                            <span>Bid: {(selectedTick.bid ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                            <span>Ask: {(selectedTick.ask ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                            <span>Vol: {(selectedTick.volume ?? 0).toLocaleString("en-IN")}</span>
                        </div>
                    </div>

                    <SymbolSearchBar
                        query={searchQuery}
                        selectedSymbol={selectedSymbol}
                        selectedExchange={selectedExchange}
                        results={searchResults}
                        loading={searchLoading}
                        error={searchError}
                        onQueryChange={setSearchQuery}
                        onSelect={applySearchSelection}
                        onSubmit={submitSearchSelection}
                    />
                </div>

                <div style={styles.grid}>

                    <div style={styles.market}>
                        <LiveMarketPanel data={liveData} />
                    </div>

                    <div style={styles.analytics}>
                        <AnalyticsDashboard data={analyticsData} />
                    </div>

                    <div style={styles.optionChain}>
                        <OptionChainHeatmap data={optionChainData} />
                    </div>

                    <div style={styles.signals}>
                        <AISignalPanel data={{
                            ...selectedSignal,
                            symbol: selectedSignal?.symbol || selectedSymbol,
                            onTakeTrade: handleTakeTrade
                        }} />
                    </div>

                    <div style={styles.greeks}>
                        <GreeksPanel data={{
                            ...selectedGreeks,
                            symbol: selectedGreeks?.symbol || selectedSymbol
                        }} />
                    </div>

                    <div style={styles.pnl}>
                        <PnlCurveChart data={streamState.pnl} />
                    </div>

                    <div style={styles.control}>
                        <StrategyControlPanel system={system} />
                    </div>

                    <div style={styles.health}>
                        <SystemHealthWidget system={system} />
                    </div>

                </div>

                {/* Floating Order Panel Button - Bottom Right */}
                <button
                    style={styles.orderPanelTab}
                    onClick={() => setShowOrderPanel(true)}
                >
                    📝 Order Panel
                </button>

                {/* Order Panel Modal/Overlay */}
                {showOrderPanel && (
                    <div style={styles.orderPanelOverlay} onClick={() => setShowOrderPanel(false)}>
                        <div style={styles.orderPanelModal} onClick={(e) => e.stopPropagation()}>
                            <div style={styles.orderPanelHeader}>
                                <h2 style={styles.orderPanelTitle}>📝 Place Order</h2>
                                <button 
                                    style={styles.orderPanelClose}
                                    onClick={() => setShowOrderPanel(false)}
                                >
                                    ✕
                                </button>
                            </div>
                            <div style={styles.orderPanelContent}>
                                <OrderPanel 
                                    selectedSymbol={prefilledTrade?.symbol || selectedSymbol}
                                    spotPrice={optionChain?.spot_price ?? undefined}
                                    onOrderPlaced={() => {
                                        setPrefilledTrade(null) // Clear prefilled data after order
                                    }}
                                    prefilledTrade={prefilledTrade}
                                />
                                <div style={styles.orderPanelDivider} />
                                <PositionPanel />
                            </div>
                        </div>
                    </div>
                )}
            </div>

        </div>
    )
}

export default MainDashboard


const styles: any = {

    container: {
        backgroundColor: spaceTheme.pageBase,
        backgroundImage: spaceTheme.pageBackground,
        color: spaceTheme.textPrimary,
        minHeight: "100dvh",
        padding: "12px 12px 18px",
        fontFamily: spaceTheme.fontFamily,
        position: "relative",
        overflowX: "hidden",
        overflowY: "auto"
    },

    backdrop: {
        position: "absolute",
        inset: 0,
        background: "#000000",
        opacity: 1
    },

    starfield: {
        position: "absolute",
        inset: 0,
        backgroundImage: spaceTheme.starfield,
        backgroundSize: "200px 200px, 280px 280px, 350px 350px, 420px 420px, 500px 500px, 600px 600px",
        backgroundPosition: "0 0, 45px 85px, 130px 35px, 30px 145px, 175px 95px, 85px 220px",
        opacity: 0.9,
        mixBlendMode: "screen",
        pointerEvents: "none"
    },

    // Galaxy outer halo - soft blue glow extending outward
    galaxyHalo: {
        position: "absolute",
        left: "-10%",
        right: "-10%",
        top: "30%",
        height: "40%",
        background: spaceTheme.galaxyHalo,
        opacity: 0.8,
        pointerEvents: "none"
    },

    // Galaxy core - bright white/blue center
    galaxyCore: {
        position: "absolute",
        left: "-5%",
        right: "-5%",
        top: "35%",
        height: "30%",
        background: spaceTheme.galaxyCore,
        opacity: 0.95,
        pointerEvents: "none",
        transform: "rotate(-15deg)"
    },

    // Galaxy dust lane - dark band across center
    galaxyDust: {
        position: "absolute",
        left: "-5%",
        right: "-5%",
        top: "35%",
        height: "30%",
        background: spaceTheme.galaxyDust,
        opacity: 0.85,
        pointerEvents: "none",
        transform: "rotate(-15deg)"
    },

    content: {
        position: "relative",
        zIndex: 1,
        display: "flex",
        flexDirection: "column",
        gap: 14
    },

    header: {
        padding: "16px 20px",
        borderBottom: "1px solid rgba(150, 180, 220, 0.15)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        gap: 18,
        flexWrap: "wrap",
        background: "linear-gradient(180deg, rgba(5, 10, 20, 0.5) 0%, rgba(2, 5, 12, 0.35) 100%)",
        backdropFilter: "blur(12px)",
        borderRadius: 20,
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), 0 10px 34px rgba(0,0,0,0.2)",
        border: "1px solid rgba(150, 180, 220, 0.12)",
        flexShrink: 0,
        position: "relative",
        zIndex: 200
    },

    headerTitle: {
        display: "flex",
        flexDirection: "column",
        gap: 4
    },

    title: {
        margin: 0,
        fontFamily: spaceTheme.titleFamily,
        fontSize: 32,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: spaceTheme.accentStrong,
        textShadow: "0 0 26px rgba(181, 171, 255, 0.24)"
    },

    subtitle: {
        color: spaceTheme.textMuted,
        fontSize: 13,
        lineHeight: 1.45,
        maxWidth: 860
    },

    liveTicker: {
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: "12px 20px",
        background: "linear-gradient(135deg, rgba(20, 30, 50, 0.9) 0%, rgba(10, 15, 30, 0.95) 100%)",
        borderRadius: 12,
        border: "1px solid rgba(100, 150, 220, 0.25)",
        boxShadow: "0 4px 20px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255,255,255,0.08)",
        flexShrink: 0
    },

    tickerSymbol: {
        fontSize: 18,
        fontWeight: 700,
        color: "#ffffff",
        letterSpacing: "0.05em"
    },

    tickerPrice: {
        fontSize: 28,
        fontWeight: 800,
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        letterSpacing: "-0.02em"
    },

    tickerChange: {
        fontSize: 14,
        fontWeight: 600,
        padding: "4px 10px",
        borderRadius: 6,
        fontFamily: "'JetBrains Mono', monospace"
    },

    tickerMeta: {
        display: "flex",
        flexDirection: "column",
        gap: 2,
        fontSize: 11,
        color: "rgba(180, 200, 230, 0.7)",
        fontFamily: "'JetBrains Mono', monospace"
    },

    searchContainer: {
        minWidth: 320,
        maxWidth: 420,
        flex: "1 1 320px",
        position: "relative",
        zIndex: 100
    },

    searchShell: {
        display: "flex",
        alignItems: "center",
        gap: 12,
        background: "linear-gradient(180deg, rgba(5, 10, 20, 0.6) 0%, rgba(2, 5, 12, 0.7) 100%)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(150, 180, 220, 0.18)",
        borderRadius: 14,
        padding: "12px 16px",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05), 0 12px 30px rgba(0,0,0,0.3)"
    },

    searchIcon: {
        color: spaceTheme.accent,
        fontSize: 13,
        letterSpacing: "0.08em",
        textTransform: "uppercase"
    },

    searchInput: {
        background: "transparent",
        border: "none",
        outline: "none",
        color: spaceTheme.textPrimary,
        width: "100%",
        fontSize: 16
    },

    searchApplyButton: {
        border: "1px solid rgba(191, 167, 255, 0.18)",
        background: "linear-gradient(180deg, rgba(146, 103, 255, 0.24) 0%, rgba(77, 205, 255, 0.18) 100%)",
        color: spaceTheme.accentStrong,
        borderRadius: 10,
        padding: "8px 12px",
        cursor: "pointer",
        fontSize: 12,
        fontWeight: 700,
        letterSpacing: "0.04em",
        flexShrink: 0
    },

    searchDropdown: {
        position: "absolute",
        top: "calc(100% + 8px)",
        left: 0,
        right: 0,
        background: "linear-gradient(180deg, rgba(5, 10, 20, 0.98) 0%, rgba(2, 5, 12, 0.99) 100%)",
        border: "1px solid rgba(150, 180, 220, 0.25)",
        borderRadius: 16,
        overflow: "hidden",
        zIndex: 9999,
        boxShadow: "0 20px 46px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.05)",
        backdropFilter: "blur(14px)"
    },

    searchState: {
        padding: 12,
        color: spaceTheme.textMuted,
        fontSize: 13
    },

    searchItem: {
        width: "100%",
        textAlign: "left",
        border: "none",
        background: "transparent",
        color: spaceTheme.textPrimary,
        padding: 14,
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        gap: 4,
        borderBottom: "1px solid rgba(151, 220, 255, 0.08)"
    },

    searchItemActive: {
        width: "100%",
        textAlign: "left",
        border: "none",
        background: "linear-gradient(90deg, rgba(152, 111, 255, 0.24) 0%, rgba(87, 210, 255, 0.1) 100%)",
        color: spaceTheme.textPrimary,
        padding: 14,
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        gap: 4,
        borderBottom: "1px solid rgba(151, 220, 255, 0.08)"
    },

    searchSymbol: {
        fontSize: 13,
        fontWeight: 700,
        letterSpacing: "0.05em"
    },

    searchMeta: {
        fontSize: 11,
        color: spaceTheme.textDim
    },

    searchRow: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 10
    },

    searchPrice: {
        fontSize: 12,
        fontWeight: 700,
        color: spaceTheme.accent
    },

    grid: {
        display: "grid",
        gridTemplateColumns: "minmax(0, 1.55fr) minmax(360px, 0.95fr) minmax(300px, 0.88fr)",
        gridTemplateRows: "minmax(470px, auto) minmax(200px, auto) minmax(200px, auto) minmax(180px, auto)",
        gap: "14px",
        alignContent: "start"
    },

    market: { ...panelShell, gridColumn: "1 / 3", gridRow: "1 / 2", padding: 12 },
    signals: { ...panelShell, gridColumn: "1 / 2", gridRow: "2 / 3", padding: 12 },
    greeks: { ...panelShell, gridColumn: "1 / 2", gridRow: "3 / 4", padding: 12 },
    pnl: { ...panelShell, gridColumn: "1 / 2", gridRow: "4 / 5", padding: 12 },
    optionChain: { ...panelShell, gridColumn: "2 / 3", gridRow: "2 / 5", padding: 12 },
    control: { ...panelShell, gridColumn: "3 / 4", gridRow: "1 / 2", padding: 12 },
    analytics: { ...panelShell, gridColumn: "3 / 4", gridRow: "2 / 3", padding: 12 },
    health: { ...panelShell, gridColumn: "3 / 4", gridRow: "3 / 5", padding: 12 },

    // Order Panel Floating Button (bottom-right corner)
    orderPanelTab: {
        position: "fixed",
        bottom: 24,
        right: 24,
        padding: "14px 28px",
        fontSize: 14,
        fontWeight: 700,
        background: "linear-gradient(135deg, rgba(0, 200, 150, 0.9) 0%, rgba(0, 150, 100, 0.95) 100%)",
        border: "none",
        borderRadius: 12,
        color: "#fff",
        cursor: "pointer",
        letterSpacing: "0.04em",
        boxShadow: "0 6px 30px rgba(0, 200, 150, 0.4), 0 2px 10px rgba(0, 0, 0, 0.3)",
        transition: "all 0.2s ease",
        zIndex: 500
    },

    // Order Panel Modal Overlay
    orderPanelOverlay: {
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0, 0, 0, 0.7)",
        backdropFilter: "blur(8px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000
    },

    orderPanelModal: {
        width: "90%",
        maxWidth: 900,
        maxHeight: "90vh",
        background: "linear-gradient(180deg, rgba(8, 15, 28, 0.98) 0%, rgba(5, 10, 20, 0.99) 100%)",
        border: "1px solid rgba(130, 234, 255, 0.25)",
        borderRadius: 20,
        boxShadow: "0 30px 80px rgba(0, 0, 0, 0.6), 0 0 60px rgba(130, 234, 255, 0.1)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column"
    },

    orderPanelHeader: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "16px 24px",
        borderBottom: "1px solid rgba(130, 234, 255, 0.15)",
        background: "rgba(0, 0, 0, 0.3)"
    },

    orderPanelTitle: {
        margin: 0,
        fontSize: 20,
        fontWeight: 700,
        color: spaceTheme.textPrimary,
        letterSpacing: "0.04em"
    },

    orderPanelClose: {
        width: 36,
        height: 36,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 18,
        background: "rgba(255, 100, 100, 0.15)",
        border: "1px solid rgba(255, 100, 100, 0.3)",
        borderRadius: 8,
        color: spaceTheme.negative,
        cursor: "pointer"
    },

    orderPanelContent: {
        display: "grid",
        gridTemplateColumns: "1fr 1px 1fr",
        gap: 0,
        flex: 1,
        overflow: "auto",
        padding: 20
    },

    orderPanelDivider: {
        background: "rgba(130, 234, 255, 0.15)",
        margin: "0 20px"
    }

}
