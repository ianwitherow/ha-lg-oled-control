#!/usr/bin/env python3
"""LG OLED TV Control - Proof of Concept CLI"""

import argparse
import asyncio
from bscpylgtv import WebOsClient
from websockets.exceptions import ConnectionClosed, WebSocketException


DEFAULT_IP = ""  # Set your TV's IP here, or use --ip argument
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


async def connect_with_retry(ip, max_retries=MAX_RETRIES):
    """Connect to TV with retry logic."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Connecting to TV at {ip}..." + (f" (attempt {attempt}/{max_retries})" if attempt > 1 else ""))
            client = await WebOsClient.create(ip, ping_interval=None, states=[])
            await client.connect()
            print("Connected!")
            return client
        except (TimeoutError, asyncio.CancelledError, ConnectionError, OSError, WebSocketException) as e:
            last_error = e
            if attempt < max_retries:
                delay = RETRY_DELAY * attempt  # exponential backoff
                print(f"Connection failed: {type(e).__name__}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                print(f"Connection failed after {max_retries} attempts.")
    raise last_error


async def main():
    parser = argparse.ArgumentParser(description="Control LG OLED TV settings")

    # Connection
    parser.add_argument("--ip", default=DEFAULT_IP, help=f"TV IP address (default: {DEFAULT_IP})")

    # Picture settings
    parser.add_argument("--brightness", type=int, metavar="0-100", help="Set OLED backlight brightness (0-100)")
    parser.add_argument("--contrast", type=int, metavar="0-100", help="Set contrast (0-100)")

    # Power
    parser.add_argument("--power-off", action="store_true", help="Turn off the TV")

    # Volume
    parser.add_argument("--volume-up", action="store_true", help="Increase volume")
    parser.add_argument("--volume-down", action="store_true", help="Decrease volume")

    # Channel
    parser.add_argument("--channel-up", action="store_true", help="Next channel")
    parser.add_argument("--channel-down", action="store_true", help="Previous channel")

    args = parser.parse_args()

    # Validate IP
    if not args.ip:
        parser.error("TV IP address required. Use --ip or set DEFAULT_IP in script.")

    # Validate brightness/contrast ranges
    if args.brightness is not None and not 0 <= args.brightness <= 100:
        parser.error("Brightness must be between 0 and 100")
    if args.contrast is not None and not 0 <= args.contrast <= 100:
        parser.error("Contrast must be between 0 and 100")

    client = await connect_with_retry(args.ip)

    try:
        # Power off
        if args.power_off:
            print("Powering off TV...")
            await client.power_off()
            return

        # Volume control
        if args.volume_up:
            await client.volume_up()
            print("Volume increased")
        if args.volume_down:
            await client.volume_down()
            print("Volume decreased")

        # Channel control
        if args.channel_up:
            await client.channel_up()
            print("Channel up")
        if args.channel_down:
            await client.channel_down()
            print("Channel down")

        # Picture settings
        if args.brightness is not None or args.contrast is not None:
            settings = {}
            if args.brightness is not None:
                settings["backlight"] = args.brightness
            if args.contrast is not None:
                settings["contrast"] = args.contrast

            print(f"Setting picture: {settings}")
            await client.set_settings("picture", settings)

        # Always show current picture values
        current = await client.get_picture_settings(["backlight", "contrast"])
        print(f"Current settings: backlight={current.get('backlight')}, contrast={current.get('contrast')}")

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
