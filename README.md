# Rise Garden (Local) for Home Assistant

A custom Home Assistant integration that controls a [Rise Gardens](https://risegardens.com/) indoor garden **entirely over your local network**. It does not use the Rise cloud, your Rise account or the internet. It talks directly to the garden's ESP32 controller on TCP port 1000.

## Features

- **Grow lights**: three independently dimmable channels (0-100%)
- **Light schedule**: edit it from the device page in local time (lights-on time, light hours, peak brightness and sunrise/sunset ramp), see it as a sensor, or set arbitrary steps with the `rise_garden_local.set_light_schedule` action
- **Daylight saving**: the controller runs on UTC, so the integration shifts the schedule when your UTC offset changes
- **Pump**: manual on/off switch, plus a pump current sensor (mA) that shows whether it is actually running
- **Pump schedule**: run time and rest time, editable, plus a summary sensor ("5 min every 60 min")
- **Clock sync**: keeps the controller's clock correct from Home Assistant, so schedules keep working without internet/NTP
- **Diagnostics**: Wi-Fi signal, controller time, and whether the controller still has a cloud (MQTT) connection

The controller runs its light schedule and pump cycle on its own, so the garden keeps working even when Home Assistant is down.

## Installation

### HACS

1. Open HACS in Home Assistant
2. Click the three dots in the top right corner and choose **Custom repositories**
3. Add this repository URL with category **Integration**
4. Search for **Rise Garden (Local)**, install it, and restart Home Assistant

### Manual

1. Copy the `custom_components/rise_garden_local` folder into your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Give the garden controller a fixed IP address (DHCP reservation) on your router
2. Go to **Settings** → **Devices & Services** → **Add Integration**
3. Search for **Rise Garden (Local)**
4. Enter the controller's IP address (port `1000` is the default)

No username or password is needed.

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| Grow light 1, 2, 3 | Light | One per light channel, with brightness |
| Lights on | Time | When the schedule starts (local time, sunrise ramp included) |
| Light hours | Number | Total time the lights are on each day, ramps included |
| Peak brightness | Number | Brightness during the main part of the day (%) |
| Sunrise/sunset ramp | Number | Length of each ramp in minutes (0 = no ramp). Each ramp has 3 steps at 25/50/75% of peak |
| Light schedule | Sensor | Summary such as `07:00-23:00`. Attributes `steps` (local time) and `steps_utc` |
| Pump | Switch | Turns the water pump on or off |
| Pump current | Sensor | Pump motor current in mA (about 200 mA while running, 0 when off) |
| Pump run time / Pump rest time | Number | Pump cycle in seconds (for example 300 s on, 3300 s off) |
| Pump schedule | Sensor | Summary such as `5 min every 60 min` |
| Wi-Fi signal | Sensor | Controller Wi-Fi RSSI (diagnostic) |
| Wi-Fi network | Sensor | SSID the controller is joined to (diagnostic) |
| Controller time | Sensor | The controller's clock (diagnostic) |
| Cloud connection | Binary sensor | Whether the controller is still connected to the Rise cloud (diagnostic) |

The firmware version appears on the device page.

Editing any of the four light-schedule settings rewrites the whole schedule from those four values. A custom schedule set from the Rise app or the action below is then replaced. The settings always show the closest match to whatever schedule is on the controller.

The controller's own schedule and pump cycle keep running. A brightness or pump state you set by hand will likely be replaced at the next schedule step or pump cycle.

## Actions

### `rise_garden_local.set_light_schedule`

For schedules the four settings can't express. Replaces the controller's **whole** light schedule. Times are **UTC**, because the controller's clock runs on UTC. It uses the same keys as the Light schedule sensor's `steps_utc` attribute, so you can copy that attribute, edit it and send it back.

```yaml
action: rise_garden_local.set_light_schedule
data:
  steps:
    - {start_utc: "11:00:00", duration_s: 2400, level: 25}
    - {start_utc: "11:40:00", duration_s: 2400, level: 50}
    - {start_utc: "12:20:00", duration_s: 2400, level: 75}
    - {start_utc: "13:00:00", duration_s: 43200}          # level defaults to 100
    - {start_utc: "01:00:00", duration_s: 2400, level: 75}
    - {start_utc: "01:40:00", duration_s: 2400, level: 50}
    - {start_utc: "02:20:00", duration_s: 2400, level: 25}
```

The controller accepts command lines of at most 127 characters, and a malformed or cut-off schedule command **erases** the schedule. To prevent that, the integration sends the shortest form the firmware accepts, refuses a schedule that would still be too long, and reads the schedule back afterwards to check it. In practice about 7 steps fit.

Daylight-saving shifts apply only to schedules written through the light-schedule settings. A schedule sent with this action keeps its UTC times, so it moves by an hour in local time when the clocks change.

### `rise_garden_local.send_command`

Sends a raw command line to the controller and returns its reply. Use it for exploring and debugging. Some commands change settings stored on the controller, so be careful.

## Going fully offline

Once the integration works, you can block the controller's internet access on your router. The **Cloud connection** sensor will turn off, while the lights, the schedule, the pump cycle and clock sync keep working. The Rise app will no longer be able to reach the garden.

## Controller protocol

The controller accepts plaintext commands, one per line ending in `\r\n`, and replies with `OK <value>` or `FAIL syntax`. It handles only one client at a time and can lock up if it gets several connections at once, so the integration sends one command at a time.

| Command | Meaning |
|---------|---------|
| `lamp <1-3>` / `lamp <1-3> <0-100>` | Read / set a light channel |
| `wpump` / `wpump on\|off` | Read / set the pump |
| `wpcurrent` | Pump current (mA) |
| `wpc` / `wpc <on_s> <off_s>` | Read / set the pump cycle. Non-numeric values silently become `0 0` |
| `ltimer` / `ltimer set <H>:<MM>:<SS>[%level]#<seconds> ...` | Read / replace the light schedule (UTC) |
| `time` / `time HH:MM:SS` | Read / set the clock (UTC time of day only; the date cannot be set) |
| `rssi`, `mqtt`, `unitid`, `fwrev` | Diagnostics |

Verified on firmware `2012 v4.3.1`.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Disclaimer

This is an unofficial integration and is not affiliated with Rise Gardens. Use at your own risk.
