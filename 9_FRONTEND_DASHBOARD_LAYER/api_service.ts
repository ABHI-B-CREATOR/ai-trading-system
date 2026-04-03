import { wsClient } from "./websocket_client"

type StreamState = {
    market: Record<string, any>
    signal: Record<string, any>
    pnl: Record<string, any>
    system: Record<string, any>
    candles: Record<string, any[]>
    greeks: Record<string, any>
    analytics: Record<string, any>
}

export type ChartHistoryResponse = {
    type: string
    symbol: string
    interval: string
    count: number
    source: string
    error?: string | null
    candles: any[]
}

export type SymbolSearchResult = {
    symbol: string
    tradingsymbol: string
    name: string
    exchange: string
    segment?: string
    instrument_token?: number
    last_price?: number | null
}

export type SymbolSearchResponse = {
    type: string
    query: string
    count?: number
    results: SymbolSearchResult[]
}

export type WatchSymbolResponse = {
    status: string
    symbol?: string
    exchange?: string
    instrument_token?: number
    message?: string
}

export type OptionChainStrike = {
    strike: number
    call_oi: number
    put_oi: number
    call_ltp: number
    put_ltp: number
    call_volume: number
    put_volume: number
}

export type OptionChainResponse = {
    type: string
    symbol: string
    expiry?: string | null
    spot_price?: number | null
    atm_strike?: number | null
    strikes: OptionChainStrike[]
}

export const getBackendBaseUrl = (): string => {
    const host = window.location.hostname || "localhost"
    const protocol = window.location.protocol === "https:" ? "https" : "http"
    return `${protocol}://${host}:8000`
}

class ApiService {

    private state: StreamState = {
        market: {},
        signal: {},
        pnl: {},
        system: {},
        candles: {},
        greeks: {},
        analytics: {}
    }

    private listeners: Array<(state: StreamState) => void> = []

    constructor() {
        wsClient.connect()

        wsClient.subscribe((data: any) => {
            this._handleStream(data)
        })
    }

    // ------------------------------------------------

    private _handleStream(data: any): void {

        console.log("🔄 _handleStream called with:", data)

        if (data.type === "snapshot" || data.type === "stream") {

            this.state.market = data.market ?? {}
            this.state.signal = data.signal ?? {}
            this.state.pnl = data.pnl ?? {}
            this.state.system = data.system ?? {}
            this.state.candles = data.candles ?? {}
            this.state.greeks = data.greeks ?? {}
            this.state.analytics = data.analytics ?? {}

            console.log("✅ State updated:", this.state)
            this._notify()
        }
    }

    // ------------------------------------------------

    private _notify(): void {
        console.log(`📢 Notifying ${this.listeners.length} listeners with state:`, this.state)
        this.listeners.forEach((cb, idx) => {
            console.log(`  → Calling listener ${idx + 1}`)
            cb(this.state)
        })
    }

    // ------------------------------------------------

    subscribe(callback: (state: StreamState) => void): void {
        console.log("🔗 Component subscribed to stream updates")
        this.listeners.push(callback)
    }

    // ------------------------------------------------
    // ===== GETTERS FOR UI PANELS =====

    getMarket(): Record<string, any> {
        return this.state.market
    }

    getSignal(): Record<string, any> {
        return this.state.signal
    }

    getPnL(): Record<string, any> {
        return this.state.pnl
    }

    getSystem(): Record<string, any> {
        return this.state.system
    }

    getCandles(): Record<string, any[]> {
        return this.state.candles
    }

    async fetchChartHistory(symbol: string, interval: string, days: number, limit: number = 300, exchange?: string): Promise<ChartHistoryResponse> {
        const params = new URLSearchParams({
            symbol,
            interval,
            days: String(days),
            limit: String(limit)
        })

        if (exchange) {
            params.set("exchange", exchange)
        }

        const response = await fetch(`${getBackendBaseUrl()}/api/data/chart_history?${params.toString()}`)
        if (!response.ok) {
            throw new Error(`Chart history request failed (${response.status})`)
        }

        return response.json() as Promise<ChartHistoryResponse>
    }

    async searchSymbols(query: string, limit: number = 20, exchanges?: string[]): Promise<SymbolSearchResponse> {
        const params = new URLSearchParams({
            query,
            limit: String(limit)
        })

        if (Array.isArray(exchanges)) {
            exchanges.forEach((exchange) => params.append("exchange", exchange))
        }

        const response = await fetch(`${getBackendBaseUrl()}/api/data/symbol_search?${params.toString()}`)
        if (!response.ok) {
            throw new Error(`Symbol search failed (${response.status})`)
        }

        return response.json() as Promise<SymbolSearchResponse>
    }

    async watchSymbol(symbol: string, exchange: string = "NSE"): Promise<WatchSymbolResponse> {
        const response = await fetch(`${getBackendBaseUrl()}/api/data/watch_symbol`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol, exchange })
        })

        if (!response.ok) {
            throw new Error(`Watch symbol failed (${response.status})`)
        }

        return response.json() as Promise<WatchSymbolResponse>
    }

    async fetchOptionChain(symbol: string, strikeCount: number = 12, exchange?: string): Promise<OptionChainResponse> {
        const params = new URLSearchParams({
            symbol,
            strike_count: String(strikeCount)
        })

        if (exchange) {
            params.set("exchange", exchange)
        }

        const response = await fetch(`${getBackendBaseUrl()}/api/data/option_chain?${params.toString()}`)
        if (!response.ok) {
            throw new Error(`Option chain request failed (${response.status})`)
        }

        return response.json() as Promise<OptionChainResponse>
    }

}

export const apiService = new ApiService()
