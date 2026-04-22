# JaredAndroids

Toolkit for provisioning a factory-reset Android 10 device (Verizon Nokia
2V Tella, in this case) as a Device Owner using Google's open-source
**TestDPC** and the standard QR-code provisioning flow — then removing
TestDPC afterward for a clean phone. The point is to get past the setup
wizard when there is no cellular service to activate against.

> Only use this on a device you own. The flow requires a factory-reset
> phone with no accounts yet configured; Device Owner can't be set once
> a user is provisioned.

## What's in here

```
scripts/compute_checksum.sh   # APK signing-cert SHA-256 -> base64url (no padding)
scripts/generate_qr.py        # builds provisioning.json (+ PNG via `qrcode`)
scripts/serve.sh              # python http.server wrapper, prints LAN URLs
out/                          # generated artifacts land here
```

## One-time setup on your laptop

1. Download the latest signed TestDPC APK from the official repo's
   releases page:
   <https://github.com/googlesamples/android-testdpc/releases>
   (Save it as `out/testdpc.apk`.)

2. Install Python QR support (only needed if you want a PNG directly):

   ```
   pip install 'qrcode[pil]'
   ```

3. `keytool` needs to be on PATH (any JDK works). If you only have
   `openssl` + `unzip`, the script falls back to those automatically.

## Step 1 — Compute the signature checksum

Android 7.0+ expects `PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM` to be
the SHA-256 of the APK's **signing certificate** (not the APK bytes),
encoded as URL-safe base64 without padding.

```
./scripts/compute_checksum.sh out/testdpc.apk
```

Example output:

```
SHA-256 (hex):        6a8b...<long hex>...
SIGNATURE_CHECKSUM:   aouLr...<base64url>...
```

Copy the `SIGNATURE_CHECKSUM` value.

## Step 2 — Start the local APK server

The Nokia has no data, so you'll host the APK on your laptop and point
the phone at it over shared Wi-Fi.

```
./scripts/serve.sh
```

It serves `./out/` on `:8000` and prints every LAN URL like
`http://192.168.1.23:8000/testdpc.apk`. Pick the one on the same subnet
as the Wi-Fi network the phone will join.

Leave this running in its own terminal.

## Step 3 — Generate the QR

In a second terminal:

```
./scripts/generate_qr.py \
  --url       http://192.168.1.23:8000/testdpc.apk \
  --checksum  aouLr...<base64url>... \
  --wifi-ssid 'YourWifi' \
  --wifi-password 'yourpassword' \
  --wifi-security WPA
```

This writes:

* `out/provisioning.json` — the exact JSON the QR encodes.
* `out/provisioning.png` — a QR image (open full-size on a second
  screen so the phone camera can focus cleanly).

The `--wifi-*` flags are optional but strongly recommended on this
device: the setup wizard has no Wi-Fi connection yet when you scan, so
including Wi-Fi credentials in the QR lets the provisioner join the
network before downloading the APK. If you skip them, the wizard will
prompt you to pick Wi-Fi first and then scan again.

The fixed fields in the payload are:

| Extra | Value |
| --- | --- |
| `PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME` | `com.afwsamples.testdpc/com.afwsamples.testdpc.DeviceAdminReceiver` |
| `PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION` | your `--url` |
| `PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM` | your `--checksum` |
| `PROVISIONING_SKIP_ENCRYPTION` | `true` |

## Step 4 — Provision the phone

1. Factory-reset the Nokia if it isn't already. You want the first
   Welcome screen, before any account setup.
2. On the Welcome screen, **tap the screen 6 times in the same spot**.
   Android 10 launches the QR-code scanner.
3. If you did not include Wi-Fi in the QR, the wizard will ask you to
   join Wi-Fi first, then return to the scanner.
4. Point the camera at `out/provisioning.png`.
5. Accept the provisioning prompt. The phone downloads the APK from
   your laptop, verifies the signing cert against the checksum,
   installs TestDPC, and sets it as Device Owner.
6. Finish the wizard. Skipping Google sign-in and SIM activation is
   fine — Device Owner mode doesn't require either.

## Step 5 — Clean the phone

Once you're at the home screen:

1. Open **TestDPC**.
2. Scroll to **Remove Device Owner** (the exact label varies by
   version — it's under the "Manage device owner" section) and
   confirm. TestDPC calls `clearDeviceOwnerApp()` on itself.
3. Uninstall TestDPC the normal way: long-press → Uninstall, or
   Settings → Apps → TestDPC → Uninstall.

The phone is now a stock Android 10 device with no Device Owner, no
TestDPC, and setup wizard already completed.

## Troubleshooting

* **"Can't set up device" / checksum mismatch.** You almost certainly
  passed the APK file hash instead of the signing-cert hash. Rerun
  `compute_checksum.sh`; it hashes the cert.
* **"Couldn't download app."** The phone can't reach the URL. Verify
  from the phone's browser first, or try `curl` from another device on
  the same Wi-Fi. Corporate or guest networks often block client-to-
  client traffic.
* **QR scanner won't open.** You need a clean factory-reset state. If
  you've already created a user, wipe again from Recovery.
* **Skip encryption ignored.** Some devices force encryption anyway.
  That's fine — provisioning still succeeds, it just reboots once.
* **Nokia 2V Tella specifics.** It's Android 10 Go edition. The 6-tap
  gesture and QR flow both work; there is no carrier lock on Device
  Owner provisioning.
