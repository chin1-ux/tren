#!/usr/bin/env bash
# Trendrop Scraper — Android Termux (Ubuntu proot) One-Time Setup
# Run this inside Termux on your Android phone (installed from F-Droid).
set -euo pipefail

echo "=== 1. Updating Termux packages ==="
pkg update -y && pkg upgrade -y
pkg install -y proot-distro git curl cronie termux-api

echo "=== 2. Installing Ubuntu inside proot-distro (needed for Firefox/Camoufox) ==="
if ! proot-distro login ubuntu -- true >/dev/null 2>&1; then
    proot-distro install ubuntu || true
fi

echo "=== 3. Setting up Python + Camoufox + Trendrop inside Ubuntu ==="
proot-distro login ubuntu -- bash -lc '
set -euo pipefail
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git curl wget \
    libgtk-3-0 libdbus-glib-1-2 libxt6 libx11-xcb1 libnss3 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 \
    libasound2t64 || apt-get install -y python3 python3-pip python3-venv git curl wget \
    libgtk-3-0 libdbus-glib-1-2 libxt6 libx11-xcb1 libnss3 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2

if [ ! -d "$HOME/tren" ]; then
    git clone https://github.com/chin1-ux/tren.git "$HOME/tren"
else
    cd "$HOME/tren" && git pull origin main
fi

cd "$HOME/tren"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install playwright "camoufox[geoip]"
playwright install-deps firefox || true
playwright install chromium || true
playwright install-deps chromium || true
python3 -m camoufox fetch
'

echo "=== 4. Creating 1-Tap Termux:Widget shortcuts ==="
mkdir -p "$HOME/.shortcuts"

cat <<'EOF' > "$HOME/.shortcuts/Trendrop_India.sh"
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
mkdir -p "$HOME/trendrop_logs"
LOG="$HOME/trendrop_logs/india_$(date +%Y%m%d_%H%M%S).log"
echo "Starting India Scraper (log: $LOG)..."
proot-distro login ubuntu -- bash -lc "cd \$HOME/tren && source venv/bin/activate && export SCRAPER_MODE=india && python3 backend/cron_job.py" 2>&1 | tee "$LOG"
termux-wake-unlock
EOF

cat <<'EOF' > "$HOME/.shortcuts/Trendrop_Global.sh"
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
mkdir -p "$HOME/trendrop_logs"
LOG="$HOME/trendrop_logs/global_$(date +%Y%m%d_%H%M%S).log"
echo "Starting Global Scraper (log: $LOG)..."
proot-distro login ubuntu -- bash -lc "cd \$HOME/tren && source venv/bin/activate && export SCRAPER_MODE=global && python3 backend/cron_job.py" 2>&1 | tee "$LOG"
termux-wake-unlock
EOF

chmod +x "$HOME/.shortcuts/Trendrop_India.sh" "$HOME/.shortcuts/Trendrop_Global.sh"

echo ""
echo "Setup complete!"
echo "Next:"
echo "1. Copy your backend/.env into Ubuntu: proot-distro login ubuntu -- nano ~/tren/backend/.env"
echo "2. Add Termux:Widget to your Android home screen and tap Trendrop_India or Trendrop_Global!"
