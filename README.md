# LG OLED Control for Home Assistant

A Home Assistant custom integration for controlling LG OLED TV picture settings. Primarily designed for adjusting backlight brightness and contrast, with additional basic controls.

## Features

- **Brightness & Contrast** - Exposed as dimmable lights (works great with HomeKit)
- **Volume Up/Down** - Button entities
- **Channel Up/Down** - Button entities
- **Power Off** - Button entity
- **Power State** - Binary sensor (polls every 3 seconds)

## Installation

1. Copy `custom_components/lg_oled_control` to your Home Assistant's `custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration**
4. Search for "LG OLED Control"
5. Enter your TV's IP address
6. Accept the pairing prompt on your TV

## Requirements

- Home Assistant 2024.11 or newer
- LG WebOS TV (tested on C2 OLED)
- "LG Connect Apps" enabled on TV: **Settings → Network → LG Connect Apps**
- For backlight control: Disable **Settings → General → OLED Care → Device Self Care → Energy Saving**

## Entities Created

| Entity | Type | Description |
|--------|------|-------------|
| `light.<name>_backlight` | Light | OLED backlight (0-100%) |
| `light.<name>_contrast` | Light | Contrast (0-100%) |
| `light.<name>_brightness_contrast` | Light | Sets both together |
| `button.<name>_volume_up` | Button | Volume up |
| `button.<name>_volume_down` | Button | Volume down |
| `button.<name>_channel_up` | Button | Channel up |
| `button.<name>_channel_down` | Button | Channel down |
| `button.<name>_power_off` | Button | Turn off TV |
| `binary_sensor.<name>_power` | Binary Sensor | TV on/off state |

## Adding Custom Controls

The `bscpylgtv` library supports many more commands. To add your own:

### 1. Add a button

Edit `button.py` and add to `BUTTON_DESCRIPTIONS`:

```python
LGTVButtonEntityDescription(
    key="mute",
    name="Mute",
    icon="mdi:volume-mute",
    press_fn=lambda coord: coord.async_mute(),
),
```

Then add the method to `coordinator.py`:

```python
async def async_mute(self) -> None:
    """Toggle mute."""
    await self.async_execute("set_mute", True)
```

### 2. Add a light/slider

Edit `light.py` and add to `LIGHT_DESCRIPTIONS`:

```python
LGTVLightEntityDescription(
    key="color",
    name="Color",
    icon="mdi:palette",
    setting_key="color",
),
```

### 3. Available commands

See the [bscpylgtv documentation](https://github.com/chros73/bscpylgtv) for all available methods:

- `set_mute(mute)` - Mute/unmute
- `set_volume(level)` - Set volume (0-100)
- `set_input(input_name)` - Switch input
- `launch_app(app_id)` - Launch an app
- `play()`, `pause()`, `stop()` - Media controls
- `set_current_picture_mode(mode)` - Change picture mode
- And many more...

## CLI Tool

A standalone CLI tool (`lg_tv_control.py`) is included for testing:

```bash
pip install bscpylgtv
python lg_tv_control.py --ip 192.168.1.100 --brightness 75
```

## License

MIT
