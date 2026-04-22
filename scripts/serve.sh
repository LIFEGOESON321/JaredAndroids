#!/usr/bin/env bash
#
# serve.sh [directory] [port]
#
# Serve a directory over HTTP on your LAN so the phone being provisioned
# can download the DPC APK during QR setup. Prints every URL the phone
# might use so you can pick one reachable from its Wi-Fi network.
#
# Default: serve ./out on port 8000.

set -euo pipefail

DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)/out}"
PORT="${2:-8000}"

if [[ ! -d "$DIR" ]]; then
  echo "Not a directory: $DIR" >&2
  exit 2
fi

echo "Serving: $DIR"
echo "Port:    $PORT"
echo
echo "LAN URLs (pick one reachable from the phone's Wi-Fi):"

# Enumerate IPv4 addresses, skipping loopback. Works on Linux and macOS.
if command -v ip >/dev/null 2>&1; then
  ip -4 -o addr show scope global \
    | awk '{print $4}' | cut -d/ -f1
else
  ifconfig 2>/dev/null \
    | awk '/inet /{print $2}' \
    | grep -v '^127\.'
fi | while read -r ip; do
  [[ -z "$ip" ]] && continue
  echo "  http://$ip:$PORT/"
  for f in "$DIR"/*.apk; do
    [[ -f "$f" ]] || continue
    echo "    http://$ip:$PORT/$(basename "$f")"
  done
done

echo
echo "Ctrl-C to stop."
echo

cd "$DIR"
exec python3 -m http.server "$PORT"
