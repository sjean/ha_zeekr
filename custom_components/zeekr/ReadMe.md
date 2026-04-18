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
