#!/usr/bin/env bash
#
# compute_checksum.sh <path-to-apk>
#
# Derives PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM for Android 7.0+
# Device Owner QR-code provisioning.
#
# Android 7.0+ expects the SHA-256 of the APK's signing certificate
# (X.509 DER bytes), encoded as URL-safe base64 WITHOUT padding.
# Ref: android.app.admin.DevicePolicyManager
#      EXTRA_PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM
#
# Works with an APK signed with v1 (jar) signature. TestDPC releases are
# v1-signed, so `keytool -printcert -jarfile` is the simplest portable path.

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <path-to-apk>" >&2
  exit 2
fi

APK="$1"
if [[ ! -f "$APK" ]]; then
  echo "Not a file: $APK" >&2
  exit 2
fi

have() { command -v "$1" >/dev/null 2>&1; }

# Preferred path: keytool reads the cert straight from the jar entry.
if have keytool; then
  HEX=$(keytool -printcert -jarfile "$APK" \
        | awk -F': ' '/SHA256:/ {print $2; exit}' \
        | tr -d ' :' \
        | tr '[:upper:]' '[:lower:]')
else
  # Fallback: extract CERT.RSA or CERT.DSA and hash the signing cert DER.
  have openssl || { echo "Need keytool or openssl installed." >&2; exit 3; }
  TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
  unzip -p "$APK" 'META-INF/*.RSA' >"$TMP/cert.p7b" 2>/dev/null \
    || unzip -p "$APK" 'META-INF/*.DSA' >"$TMP/cert.p7b"
  openssl pkcs7 -inform DER -in "$TMP/cert.p7b" -print_certs -out "$TMP/cert.pem"
  HEX=$(openssl x509 -in "$TMP/cert.pem" -outform DER \
        | openssl dgst -sha256 -hex \
        | awk '{print $NF}')
fi

if [[ -z "${HEX:-}" ]]; then
  echo "Failed to compute SHA-256 of the signing cert." >&2
  exit 4
fi

# hex -> raw -> base64url without padding
B64URL=$(printf '%s' "$HEX" \
  | python3 -c '
import sys, base64, binascii
h = sys.stdin.read().strip()
raw = binascii.unhexlify(h)
print(base64.urlsafe_b64encode(raw).rstrip(b"=").decode())
')

echo "SHA-256 (hex):        $HEX"
echo "SIGNATURE_CHECKSUM:   $B64URL"
