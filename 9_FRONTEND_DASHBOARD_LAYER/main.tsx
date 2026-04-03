import React from "react"
import ReactDOM from "react-dom/client"
import MainDashboard from "./main_dashboard"
import "./global.css"

class DashboardErrorBoundary extends React.Component<
    { children: React.ReactNode },
    { hasError: boolean, message: string }
> {
    constructor(props: { children: React.ReactNode }) {
        super(props)
        this.state = {
            hasError: false,
            message: ""
        }
    }

    static getDerivedStateFromError(error: Error): { hasError: boolean, message: string } {
        return {
            hasError: true,
            message: error?.message || "Unknown frontend error"
        }
    }

    componentDidCatch(error: Error): void {
        console.error("Dashboard render error:", error)
    }

    render(): React.ReactNode {
        if (this.state.hasError) {
            return (
                <div style={{
                    minHeight: "100vh",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: 24,
                    color: "#d9ecff",
                    background: "linear-gradient(180deg, #07111f 0%, #0b1320 100%)",
                    fontFamily: "'Segoe UI', sans-serif"
                }}>
                    <div style={{
                        maxWidth: 720,
                        width: "100%",
                        padding: 24,
                        borderRadius: 18,
                        border: "1px solid rgba(145,220,255,0.18)",
                        background: "rgba(9, 20, 36, 0.92)",
                        boxShadow: "0 18px 60px rgba(0,0,0,0.34)"
                    }}>
                        <div style={{ fontSize: 26, fontWeight: 700, marginBottom: 10 }}>
                            Dashboard render error
                        </div>
                        <div style={{ fontSize: 14, lineHeight: 1.6, color: "rgba(217,236,255,0.82)" }}>
                            The frontend hit an error while rendering the dashboard. Refresh once. If it happens again,
                            send this message:
                        </div>
                        <pre style={{
                            marginTop: 14,
                            marginBottom: 0,
                            whiteSpace: "pre-wrap",
                            wordBreak: "break-word",
                            fontSize: 13,
                            color: "#8ee7ff"
                        }}>
                            {this.state.message}
                        </pre>
                    </div>
                </div>
            )
        }

        return this.props.children
    }
}

ReactDOM.createRoot(
    document.getElementById("root")!
).render(
    <React.StrictMode>
        <DashboardErrorBoundary>
            <MainDashboard />
        </DashboardErrorBoundary>
    </React.StrictMode>
)
