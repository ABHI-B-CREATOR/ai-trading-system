# AI Algo Trading Dashboard (Frontend)

Production-grade React + TypeScript dashboard for real-time algorithmic trading visualization.

## 📋 Architecture

```
┌─────────────────────────────┐
│  Main Dashboard             │
│  (Grid Layout)              │
├─────────────────────────────┤
│ Market │ Analytics │ Control│
│ Panel  │ Dashboard │ Panel  │
├─────────────────────────────┤
│ Signal │ PnL Curve │ Health │
│ Panel  │ Chart     │ Widget │
└────────┬──────────────────┬─┘
         │ WebSocket        │ REST API
         ↓                  ↓
    ┌─────────────────────────────┐
    │  Backend (Flask + Python)    │
    │  :8000 API                  │
    │  :8765 WebSocket            │
    └─────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Node.js 16+ and npm
- Backend running on `localhost:8000`
- WebSocket server on `localhost:8765`

### Installation

```bash
# Install dependencies
npm install

# Create environment file
cp .env.example .env

# (optional) Edit .env for custom settings
# VITE_BACKEND_URL=http://your-backend:8000
# VITE_WS_URL=ws://your-websocket:8765

# Start development server
npm run dev

# Open browser to http://localhost:3000
```

### Build for Production

```bash
npm run build
npm run preview
```

## 📊 Dashboard Components

| Component | Purpose |
|-----------|---------|
| **LiveMarketPanel** | Real-time price feeds and trend visualization |
| **AnalyticsDashboard** | Quant metrics (volatility, momentum, regime) |
| **AISignalPanel** | Strategy signals with confidence/accuracy |
| **PnlCurveChart** | Equity curve from executed trades |
| **StrategyControlPanel** | Start/stop strategies, emergency controls |
| **SystemHealthWidget** | Backend status, trading mode, risk mode |
| **OptionChainHeatmap** | Option OI visualization |

## 🔌 Data Streams

### WebSocket Events (from Backend)

```
{
  type: "snapshot" | "stream",
  market: { ltp, symbol, change_pct, volatility, momentum, regime },
  signal: { strategy, signal, action, confidence, accuracy },
  pnl: { equity: [values], trades: count },
  system: { status, mode, risk_mode }
}
```

### REST API Endpoints

```
POST /api/strategy/start
POST /api/strategy/stop
POST /api/strategy/emergency_pause
POST /api/strategy/update_params
GET  /api/trades/history
GET  /api/performance/metrics
```

## 🎨 Styling

Dark theme with color codes:
- **Bullish**: `#2ecc71` (green)
- **Bearish**: `#e74c3c` (red)
- **Neutral**: `#f1c40f` (yellow)
- **Background**: `#0b1320` (dark)
- **Panel**: `#0f1a2b` (light dark)

## ⚙️ Build Configuration

- **Build Tool**: Vite (ultra-fast)
- **Framework**: React 18.2 + TypeScript
- **Styling**: Inline CSS objects (no dependency)
- **Package Manager**: npm

## 🧪 Development

```bash
# Watch and auto-reload
npm run dev

# Type checking
npx tsc --noEmit

# Build and check output
npm run build
ls dist/
```

## 📦 Deployment

**Docker:**
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

**Environment Variables for Production:**
```bash
VITE_BACKEND_URL=https://your-api.com
VITE_WS_URL=wss://your-api.com/ws
```

## 📝 Notes

- All components are functional React components with Hooks
- State management via `apiService` singleton
- WebSocket reconnects automatically on disconnect
- TypeScript strict mode enabled for safety
- No external UI libraries (lightweight approach)

## 🔄 Integration Checklist

- ✅ WebSocket client connected
- ✅ REST API routes wired
- ✅ All 6 dashboard panels active
- ✅ Real-time data streaming
- ✅ Strategy control API
- ✅ System health monitoring
- ✅ Responsive dark theme

---

**Backend Status**: ✅ Production-ready
**Frontend Status**: ✅ Production-ready
**System Status**: ✅ Ready for deployment
