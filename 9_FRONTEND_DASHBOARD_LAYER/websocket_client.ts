type WebSocketCallback = (data: any) => void

class WebSocketClient {

    private socket: WebSocket | null = null
    private listeners: WebSocketCallback[] = []
    private reconnectAttempts: number = 0
    private maxReconnectAttempts: number = 5

    connect(): void {

        try {
            // Get the current host dynamically instead of hardcoding localhost
            const host = window.location.hostname
            const protocol = window.location.protocol === "https:" ? "wss" : "ws"
            const wsUrl = `${protocol}://${host}:8765`
            
            console.log(`🔌 Connecting to WebSocket: ${wsUrl}`)
            this.socket = new WebSocket(wsUrl)

            this.socket.onopen = (): void => {
                console.log("📡 Connected to Trading Backend Stream")
                this.reconnectAttempts = 0
            }

            this.socket.onmessage = (event: MessageEvent): void => {

                try {
                    const data = JSON.parse(event.data as string)
                    console.log("📊 Received data:", data)
                    this.listeners.forEach(cb => cb(data))
                } catch (e) {
                    console.error("Failed to parse WebSocket message", e)
                }
            }

            this.socket.onclose = (): void => {
                console.log("❌ Stream Disconnected — retrying...")
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++
                    setTimeout(() => this.connect(), 3000)
                }
            }

            this.socket.onerror = (err: Event): void => {
                console.error("WebSocket Error", err)
            }
        } catch (e) {
            console.error("WebSocket connection error", e)
        }
    }

    subscribe(callback: WebSocketCallback): void {
        this.listeners.push(callback)
    }
}

export const wsClient = new WebSocketClient()
