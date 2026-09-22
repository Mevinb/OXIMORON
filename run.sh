#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "=================================================="
echo "          Starting OXIMORON Platform              "
echo "=================================================="

# Check toolchain prerequisites
if ! command -v uv &> /dev/null; then
    echo "[!] 'uv' is not installed or not in PATH."
    exit 1
fi

if ! command -v pnpm &> /dev/null; then
    echo "[!] 'pnpm' is not installed or not in PATH."
    exit 1
fi

# Process cleanup handler
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "[*] Shutting down OXIMORON processes..."
    if [ -n "$BACKEND_PID" ]; then
        kill -TERM "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill -TERM "$FRONTEND_PID" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo "[✓] Shutdown complete."
}
trap cleanup EXIT INT TERM

# Handle arguments
START_BACKEND=true
START_FRONTEND=true

case "$1" in
    --backend-only)
        START_FRONTEND=false
        ;;
    --desktop-only)
        START_BACKEND=false
        ;;
esac

# 1. Start Supervisor Backend
if [ "$START_BACKEND" = true ]; then
    echo "[*] Launching OXIMORON Supervisor Backend on 127.0.0.1:6969..."
    uv run oximoron-backend &
    BACKEND_PID=$!

    # Wait for backend readiness probe
    echo "[*] Waiting for backend to initialize..."
    READY=false
    for i in {1..30}; do
        if curl -s http://127.0.0.1:6969/api/v1/health > /dev/null 2>&1; then
            READY=true
            break
        fi
        sleep 0.5
    done

    if [ "$READY" = true ]; then
        echo "[✓] Backend is online and ready!"
    else
        echo "[!] Backend failed to report ready within 15 seconds."
    fi
fi

# 2. Start Desktop Frontend
if [ "$START_FRONTEND" = true ]; then
    echo "[*] Launching OXIMORON Desktop UI (Vite dev server on port 5173)..."
    pnpm --filter @oximoron/desktop dev &
    FRONTEND_PID=$!

    # Wait briefly and attempt to open browser if in desktop session
    sleep 2
    if command -v xdg-open &> /dev/null && [ -n "$DISPLAY" ]; then
        xdg-open "http://localhost:5173" &> /dev/null &
    fi

    echo "--------------------------------------------------"
    echo "  OXIMORON Desktop UI: http://localhost:5173     "
    echo "  Supervisor Backend:  http://127.0.0.1:6969     "
    echo "  Press Ctrl+C to stop all services               "
    echo "--------------------------------------------------"
fi

# Wait for children
wait
