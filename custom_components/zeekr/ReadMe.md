# Zeekr Integration for Home Assistant

This integration lets Home Assistant retrieve data from your Zeekr vehicle.

## Features

- Battery charge level
- Vehicle GPS location
- Interior and exterior temperature
- Door and window status
- Tire pressure
- Maintenance information
- Odometer and speed
- Air quality

## Installation

### Option 1: HACS (Recommended)

1. Open HACS in Home Assistant.
2. Go to `Integrations`.
3. Click the three-dot menu in the top-right corner.
4. Select `Custom repositories`.
5. Add the URL: `https://github.com/asafov_s/ha_zeekr`
6. Click `INSTALL`

### Option 2: Manual

1. Download the `zeekr` folder from `custom_components/`.
2. Copy it to `config/custom_components/`.
3. Restart Home Assistant.

## Setup

1. Go to **Settings -> Devices & Services -> Integrations**
2. Click **Add Integration**
3. Search for **Zeekr**
4. Enter your phone number in the format `13812345678`
5. Enter the SMS code
6. Done

## Supported Sensors

### Sensors

- Battery (%)
- Distance to Empty (km)
- Interior Temperature (°C)
- Exterior Temperature (°C)
- Odometer (km)
- Current Speed (km/h)
- Average Speed (km/h)
- Days to Service
- Distance to Service (km)
- Tire Pressures (kPa)
- Interior PM2.5 (μg/m³)

### Binary Sensors

- Engine Status
- Door Status (4 doors)
- Trunk Status
- Hood Status
- Window Status (4 windows)

### Device Tracker

- Vehicle Location (GPS)

## Update Interval

By default, data refreshes every **5 minutes**.

To change the interval, edit `const.py`:

```python
DEFAULT_SCAN_INTERVAL = 300  # 300 seconds = 5 minutes
```

## Remote-Control Analysis Tools

The repository also contains helper scripts for analyzing the mainland-China
mobile app's `remoteControl/control` requests:

- `scripts/replay_cn_remote_control_from_logcat.py`
  Extract the latest signed request from `adb logcat` and replay it.
- `scripts/compare_cn_remote_control_signature.py`
  Compare the captured real `x-signature` against the candidate visible
  signing variants implemented in this repository.
- `scripts/archive_cn_remote_control_sample.py`
  Save captured signed requests to JSON files under
  `artifacts/remote_control_samples/` for later inspection.
- `scripts/analyze_cn_remote_control_samples.py`
  Compare multiple archived samples to surface stable fields, changing fields,
  header order consistency, and nonce / timestamp patterns.

Typical workflow:

1. Capture and archive several successful app requests.
2. Run the batch analyzer over the archived samples.
3. Run the compare tool on a fresh sample to see whether any visible signing
   variant matches the real app signature.
4. Use the replay tool to verify whether an already-signed app request is still
   accepted by the gateway.

## Current Remote-Control Findings

The current state of the mainland-China remote-control investigation is:

- Replaying a real signed `remoteControl/control` request captured from logcat
  reaches the gateway business layer and returns `00A19` duplicate request,
  instead of `00A06` signature failure. That indicates the captured app request
  itself is valid.
- The visible candidate formulas implemented in this repository do not match
  the real app's `x-signature` on captured successful samples.
- Matching `authorization`, device ID, vehicle identifier, vehicle series,
  URL, and JSON body is not sufficient to reproduce the app signature.
- Based on the current evidence, the signing path used by the mobile app is
  protected and differs from the visible Java-like formula currently modeled in
  this repository.

### Five-Sample Stability Summary

Five successful `remoteControl/control` samples were archived and compared:

- `sample1-1776500723247-42e135d5.json`
- `sample2-1776500747315-b4cdd01d.json`
- `sample3-1776500765597-3ed7272a.json`
- `sample4-1776508565988-957d0cb1.json`
- `sample5-1776508629672-c857a049.json`

Across all five successful samples, the following request fields remained
stable:

- `accept`
- `accept-language`
- `authorization`
- `content-type`
- `x-api-signature-version`
- `x-app-id`
- `x-app-version`
- `x-device-brand`
- `x-device-id`
- `x-device-model`
- `x-device-os-version`
- `x-platform`
- `x-sales-platform`
- `x-tenant-id`
- `x-tsp-platform`
- `x-vehicle-brand`
- `x-vehicle-identifier`
- `x-vehicle-series`

Only the following fields changed on each successful request:

- `x-api-signature-nonce`
- `x-timestamp`
- `x-signature`

The header order was identical in all five successful samples:

```text
accept -> accept-language -> authorization -> content-type ->
x-api-signature-nonce -> x-api-signature-version -> x-app-id ->
x-app-version -> x-device-brand -> x-device-id -> x-device-model ->
x-device-os-version -> x-platform -> x-sales-platform -> x-signature ->
x-tenant-id -> x-timestamp -> x-tsp-platform -> x-vehicle-brand ->
x-vehicle-identifier -> x-vehicle-series
```

Additional observations from the five-sample batch analysis:

- All five `x-api-signature-nonce` values were unique.
- The observed request timestamps covered a broad window, but the stable header
  set and stable header order remained unchanged.
- None of the currently modeled visible signing variants matched the real
  `x-signature` for any of the five successful samples.

### Recommended Investigation Conclusions

Based on the replay, compare, archive, and five-sample batch analysis, the
recommended working conclusion is:

- A real app-signed request can be replayed and still pass gateway signature
  validation, which means the captured request context is valid and reaches the
  business layer.
- The current visible signing models in this repository consistently miss the
  real `x-signature`, even when replaying the same request context captured from
  the app.
- The remote-control request context appears stable within a session; the main
  per-request changes are `nonce`, `timestamp`, and the final signature.
- The remaining gap is most likely in the protected signer implementation used
  by the app, not in ordinary request fields such as URL, body, authorization,
  device ID, vehicle identifier, or vehicle series.
- Further investigation should prioritize higher-confidence observation and
  documentation of the protected signing path, rather than continued guessing of
  visible header or body combinations.
