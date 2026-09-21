#!/usr/bin/env bash
set -euo pipefail

# Usage: ./run_chrome.sh <domain> <script_name> <prefix>
# Example: ./run_chrome.sh example.com cdn.consentmanager.net __cmpconsentx

DOMAIN="$1"
SCRIPT_NAME="$2"
COOKIE_PREFIX="$3"

# Convert domain.com → domain_com for the output file
DOMAIN_SLUG="${DOMAIN//./_}"
PROFILE_TEMPLATE_DIR=../new_selenium/profile-template
USER_DATA_DIR="./tmp/${DOMAIN_SLUG}_profile"

CHROME_BIN="../arcanum/chromium/src/out/arc/chrome"

# Ensure the Chrome binary exists
if [ ! -x "$CHROME_BIN" ]; then
  echo "Error: Chrome binary not found or not executable at: $CHROME_BIN"
  exit 2
fi

mkdir -p "$(dirname "$USER_DATA_DIR")"

# 1) remove expired template
rm -rf "$USER_DATA_DIR"

# 2) copy new profile from template
cp -r "$PROFILE_TEMPLATE_DIR" "$USER_DATA_DIR"

LOGFILE="../results_new/${DOMAIN_SLUG}.log"
FLAGFILE="../results_new/${DOMAIN_SLUG}.flag"

# 3) Run Chrome with the given js-flag and redirect stdout to domain_com
"$CHROME_BIN" \
  --disable-gpu --no-sandbox --ignore-certificate-errors \
  --disk-cache-size=0 --disk-cache-dir=/dev/null --media-cache-size=0 --memory-pressure-heuristic-period-ms=0 \
  --user-data-dir="$USER_DATA_DIR" --no-first-run --no-default-browser-check \
  --proxy-server=http://127.0.0.1:7895 \
  --js-flags="--cookie_script=${SCRIPT_NAME} --accessing_domain=${DOMAIN} --cookie_prefix=${COOKIE_PREFIX} --instance_id=1234" \
  "$DOMAIN" \
  > "$LOGFILE" 2>&1 &

CHROME_PID=$!
echo "[INFO] Launched Chrome (PID=$CHROME_PID), logging to $LOGFILE"

sleep 10

cleanup(){
  echo "[INFO] Caught SIGINT, cleaning up…"
  kill "$TAIL_PID" 2>/dev/null || true
  kill "$CHROME_PID" 2>/dev/null || true
  exit
}
trap cleanup SIGINT

tail -n0 -F "$LOGFILE" | \
while IFS= read -r line; do
  if [[ "$line" == *"[Consent-O-Matic]"* ]]; then
    echo "[INFO] Detected consent event: $line"
    touch "$FLAGFILE"
  fi
done &
TAIL_PID=$!

wait "$CHROME_PID"
echo "[INFO] Chrome exited, script end."

