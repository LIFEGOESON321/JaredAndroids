#!/usr/bin/env python3
"""
generate_qr.py — build an Android Device Owner provisioning QR.

Outputs:
  out/provisioning.json  (the raw JSON the QR encodes)
  out/provisioning.png   (the QR image, if `qrcode` is installed)

Android 10 setup wizard launches the QR scanner when you tap the Welcome
screen six times. The scanner reads a JSON blob with these extras:

  android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION
  android.app.extra.PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM
  android.app.extra.PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME
  android.app.extra.PROVISIONING_SKIP_ENCRYPTION

Optional (useful when the device has no SIM and Wi-Fi setup hasn't
happened yet — the wizard can join the network before the download):

  android.app.extra.PROVISIONING_WIFI_SSID
  android.app.extra.PROVISIONING_WIFI_PASSWORD
  android.app.extra.PROVISIONING_WIFI_SECURITY_TYPE   ("WPA" / "WEP" / "NONE")
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TESTDPC_COMPONENT = (
    "com.afwsamples.testdpc/com.afwsamples.testdpc.DeviceAdminReceiver"
)

OUT_DIR = Path(__file__).resolve().parent.parent / "out"


def build_payload(
    download_url: str,
    checksum: str,
    component: str,
    skip_encryption: bool,
    wifi_ssid: str | None,
    wifi_password: str | None,
    wifi_security: str | None,
) -> dict:
    payload: dict = {
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME": component,
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION": download_url,
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM": checksum,
        "android.app.extra.PROVISIONING_SKIP_ENCRYPTION": skip_encryption,
    }
    if wifi_ssid:
        payload["android.app.extra.PROVISIONING_WIFI_SSID"] = wifi_ssid
        payload["android.app.extra.PROVISIONING_WIFI_SECURITY_TYPE"] = (
            wifi_security or "WPA"
        )
        if wifi_password:
            payload["android.app.extra.PROVISIONING_WIFI_PASSWORD"] = wifi_password
    return payload


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", required=True,
                   help="HTTP(S) URL where the phone can download the DPC APK.")
    p.add_argument("--checksum", required=True,
                   help="SIGNATURE_CHECKSUM from compute_checksum.sh.")
    p.add_argument("--component", default=TESTDPC_COMPONENT,
                   help=f"DPC component (default: {TESTDPC_COMPONENT}).")
    p.add_argument("--skip-encryption", action="store_true", default=True,
                   help="Include PROVISIONING_SKIP_ENCRYPTION=true (default).")
    p.add_argument("--wifi-ssid", default=None)
    p.add_argument("--wifi-password", default=None)
    p.add_argument("--wifi-security", default=None, choices=[None, "WPA", "WEP", "NONE"])
    p.add_argument("--out-dir", default=str(OUT_DIR))
    args = p.parse_args()

    payload = build_payload(
        download_url=args.url,
        checksum=args.checksum,
        component=args.component,
        skip_encryption=bool(args.skip_encryption),
        wifi_ssid=args.wifi_ssid,
        wifi_password=args.wifi_password,
        wifi_security=args.wifi_security,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "provisioning.json"
    # Compact JSON keeps the QR small and scannable on a low-end camera.
    json_blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    json_path.write_text(json_blob + "\n")
    print(f"wrote {json_path}")
    print(json.dumps(payload, indent=2, sort_keys=True))

    try:
        import qrcode  # type: ignore
    except ImportError:
        print("\n(qrcode module not installed — skipping PNG.)")
        print("Install with:  pip install 'qrcode[pil]'")
        print("Or paste the JSON above into any offline QR generator.")
        return 0

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(json_blob)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    png_path = out_dir / "provisioning.png"
    img.save(png_path)
    print(f"wrote {png_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
