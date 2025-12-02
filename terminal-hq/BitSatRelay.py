#!/usr/bin/env python3
"""
BitSatRelay - Bitcoin Satellite Relay with Lightning Payments
Bridges Nostr messages to satellite with BitSatCredit extension for credit management
"""

import socket
import struct
import sys
import time
import os
import asyncio
import websockets
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Import our modules
from bitsatcredit_client import BitSatCreditClient
from nostr_bot import NostrBot
from satellite_monitor import SatelliteMonitor
from dm_bot import DMBot

# Rate limiting for satellite messages
last_message_time = 0
processed_events = set()  # Track processed event IDs to prevent duplicates
MIN_MESSAGE_INTERVAL = 5.0


class HSModemFileTransfer:
    def __init__(self, host=None, port=None):
        self.host = host or '192.168.1.112'
        self.port = port or 40132

        # HSModem protocol constants
        self.TYPE_BER_TEST = 1      # BER Test Pattern (compressed)
        self.TYPE_IMAGE = 2         # Image data (NOT compressed) - use for plain text
        self.TYPE_ASCII = 3         # ASCII File (compressed by modem)
        self.TYPE_HTML = 4          # HTML File (compressed)
        self.TYPE_BINARY = 5        # Binary File (compressed)
        self.FRAME_FIRST = 0
        self.FRAME_MIDDLE = 1
        self.FRAME_LAST = 2
        self.FRAME_SINGLE = 3
        self.TOTAL_PACKET_SIZE = 221
        self.HEADER_SIZE = 2
        self.PAYLOAD_SIZE = 219
        self.FILENAME_SIZE = 50
        self.CRC_SIZE = 2
        self.FILESIZE_SIZE = 3
        self.FIRST_FRAME_DATA_SIZE = 163
        self.max_file_size = 0x1FFFFF

    def calculate_crc16(self, data):
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0x8408
                else:
                    crc >>= 1
        return crc ^ 0xFFFF

    def create_packet(self, file_type, frame_info, payload_data):
        packet = bytearray(self.TOTAL_PACKET_SIZE)
        packet[0] = file_type
        packet[1] = frame_info
        payload_len = min(len(payload_data), self.PAYLOAD_SIZE)
        packet[2:2+payload_len] = payload_data[:payload_len]
        return bytes(packet)

    def send_packet(self, packet):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                bytes_sent = sock.sendto(packet, (self.host, self.port))
                return True, f"Sent {bytes_sent} bytes"
        except Exception as e:
            return False, f"Error: {e}"

    def send_file(self, filepath, quiet=False):
        try:
            with open(filepath, 'rb') as f:
                file_data = f.read()

            filename = Path(filepath).name
            file_size = len(file_data)

            if file_size > self.max_file_size:
                return False, f"File too large: {file_size} bytes"

            if not quiet:
                print(f"Sending: {filename} ({file_size} bytes)")

            if file_size <= self.FIRST_FRAME_DATA_SIZE:
                return self._send_single_frame(filename, file_data, quiet)
            else:
                return self._send_multi_frame(filename, file_data, quiet)

        except Exception as e:
            return False, f"Error: {e}"

    def _send_single_frame(self, filename, file_data, quiet=False):
        payload = bytearray()

        filename_bytes = filename.encode('ascii', errors='replace')[:self.FILENAME_SIZE]
        filename_field = filename_bytes.ljust(self.FILENAME_SIZE, b'\x00')
        payload.extend(filename_field)

        crc = self.calculate_crc16(filename_bytes)
        payload.extend(struct.pack('<H', crc))
        payload.extend(struct.pack('>I', len(file_data))[-3:])
        payload.extend(file_data)

        # USE TYPE_IMAGE (uncompressed - critical for proper frame reassembly)
        packet = self.create_packet(self.TYPE_IMAGE, self.FRAME_SINGLE, payload)
        success, msg = self.send_packet(packet)

        if not quiet:
            print(f"Single frame sent: {len(packet)} bytes (IMAGE MODE - uncompressed)")

        # Delay AFTER sending to ensure modem completes processing
        time.sleep(1.0)

        return success, "Single frame transmission complete"

    def _send_multi_frame(self, filename, file_data, quiet=False):
        file_size = len(file_data)
        frames_needed = self._calc_frames(file_size)

        if not quiet:
            print(f"Multi-frame transmission: {frames_needed} frames (IMAGE MODE - uncompressed)")

        filename_bytes = filename.encode('ascii', errors='replace')[:self.FILENAME_SIZE]
        filename_field = filename_bytes.ljust(self.FILENAME_SIZE, b'\x00')
        crc = self.calculate_crc16(filename_bytes)

        first_payload = bytearray()
        first_payload.extend(filename_field)
        first_payload.extend(struct.pack('<H', crc))
        first_payload.extend(struct.pack('>I', file_size)[-3:])

        first_data_chunk = file_data[:self.FIRST_FRAME_DATA_SIZE]
        first_payload.extend(first_data_chunk)

        # USE TYPE_IMAGE (uncompressed - critical for proper frame reassembly)
        packet = self.create_packet(self.TYPE_IMAGE, self.FRAME_FIRST, first_payload)
        success, msg = self.send_packet(packet)
        if not success:
            return False, f"First frame failed: {msg}"

        if not quiet:
            print(f"Frame 1/{frames_needed} sent")

        # Delay AFTER first frame to give modem time to send announcement
        time.sleep(1.0)

        remaining_data = file_data[self.FIRST_FRAME_DATA_SIZE:]
        frame_num = 2

        while remaining_data:
            # Small delay to prevent modem buffer overflow
            time.sleep(0.1)  # 100ms between frames

            chunk_size = min(len(remaining_data), self.PAYLOAD_SIZE)
            chunk = remaining_data[:chunk_size]
            remaining_data = remaining_data[chunk_size:]

            is_last = len(remaining_data) == 0
            frame_type = self.FRAME_LAST if is_last else self.FRAME_MIDDLE

            # USE TYPE_IMAGE (uncompressed - critical for proper frame reassembly)
            packet = self.create_packet(self.TYPE_IMAGE, frame_type, chunk)
            success, msg = self.send_packet(packet)
            if not success:
                return False, f"Frame {frame_num} failed: {msg}"

            if not quiet:
                print(f"Frame {frame_num}/{frames_needed} sent")

            frame_num += 1

        # Delay AFTER last frame to ensure modem completes processing
        time.sleep(1.0)

        if not quiet:
            print(f"First transmission complete - starting second pass for redundancy")

        # SECOND PASS - Retransmit entire file for error recovery
        # Receiver can use second pass to fill in missing blocks
        time.sleep(2.0)  # Gap between first and second transmission

        # Retransmit first frame
        packet = self.create_packet(self.TYPE_IMAGE, self.FRAME_FIRST, first_payload)
        success, msg = self.send_packet(packet)
        if not quiet:
            print(f"[Pass 2] Frame 1/{frames_needed} sent")

        time.sleep(1.0)  # Delay after first frame for announcement

        # Retransmit all subsequent frames
        remaining_data = file_data[self.FIRST_FRAME_DATA_SIZE:]
        frame_num = 2

        while remaining_data:
            time.sleep(0.1)  # 100ms between frames

            chunk_size = min(len(remaining_data), self.PAYLOAD_SIZE)
            chunk = remaining_data[:chunk_size]
            remaining_data = remaining_data[chunk_size:]

            is_last = len(remaining_data) == 0
            frame_type = self.FRAME_LAST if is_last else self.FRAME_MIDDLE

            packet = self.create_packet(self.TYPE_IMAGE, frame_type, chunk)
            success, msg = self.send_packet(packet)
            if not success:
                return False, f"[Pass 2] Frame {frame_num} failed: {msg}"

            if not quiet:
                print(f"[Pass 2] Frame {frame_num}/{frames_needed} sent")

            frame_num += 1

        time.sleep(1.0)

        return True, f"Multi-frame transmission complete: {frames_needed} frames × 2 passes"

    def _calc_frames(self, file_size):
        if file_size <= self.FIRST_FRAME_DATA_SIZE:
            return 1
        remaining = file_size - self.FIRST_FRAME_DATA_SIZE
        additional = (remaining + self.PAYLOAD_SIZE - 1) // self.PAYLOAD_SIZE
        return 1 + additional


def load_config():
    """Load configuration from JSON file"""
    config_path = Path(__file__).parent / "relay_config.json"

    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("Please create relay_config.json with your settings")
        sys.exit(1)

    with open(config_path, 'r') as f:
        return json.load(f)


def hex_to_npub(pubkey_hex):
    """Convert hex pubkey to npub (bech32)"""
    try:
        from nostr.key import PublicKey
        return PublicKey(bytes.fromhex(pubkey_hex)).bech32()
    except Exception as e:
        print(f"Error converting pubkey: {e}")
        return pubkey_hex  # Fallback to hex


async def handle_nostr_event(event, hsmodem_client, credit_client, nostr_bot, config):
    """Process incoming Nostr event"""
    global last_message_time, processed_events

    # Duplicate check
    event_id = event.get('id', '')
    if event_id in processed_events:
        return
    processed_events.add(event_id)
    if len(processed_events) > 50:
        processed_events.clear()

    # Extract event data
    event_kind = event.get('kind', 1)
    pubkey_hex = event.get('pubkey', '')
    created_at = event.get('created_at', int(time.time()))

    # Handle kind 6 reposts differently - they contain JSON in content
    if event_kind == 6:
        # For reposts, extract the original event from content
        try:
            reposted_event = json.loads(event.get('content', '{}'))
            # Get the original author from the reposted event
            original_author = reposted_event.get('pubkey', '')
            original_content = reposted_event.get('content', '').strip()

            # Create a meaningful message for satellite
            content = f"[REPOST] {original_content[:200]}"  # Truncate if too long
            if len(original_content) > 200:
                content += "..."
        except (json.JSONDecodeError, KeyError):
            # If we can't parse the repost, skip it
            return
    else:
        # Kind 1 (text notes) - use content directly
        content = event.get('content', '').strip()

    if not content or not pubkey_hex:
        return

    # Convert hex pubkey to npub (bech32)
    npub = hex_to_npub(pubkey_hex)

    # Check if user account exists (don't auto-create accounts)
    price_per_msg = config['pricing']['price_per_message_sats']

    user = credit_client.get_user(npub)
    if user is None:
        # User hasn't topped up yet - silently ignore (no spam, no account creation)
        return

    # User exists - check if they can afford the message
    if not credit_client.can_spend(npub, price_per_msg):
        print(f"⚠️ Insufficient credits: {npub[:16]}...")
        print(f"💡 User needs to top up at: {config['bitsatcredit_extension']['url']}")
        return

    # Rate limiting
    current_time = time.time()
    if current_time - last_message_time < MIN_MESSAGE_INTERVAL:
        print(f"⏱️ Rate limited: {npub[:16]}...")
        return

    # Deduct credits via extension API
    result = credit_client.spend_credits(npub, price_per_msg, memo="Satellite message")
    if not result:
        print(f"❌ Failed to deduct credits for {npub[:16]}...")
        return

    new_balance = result.get('balance_sats', 0)
    print(f"💰 Credits deducted: {npub[:16]}... (remaining: {new_balance} sats)")

    # Send to satellite - PLAIN TEXT JSON (no ZIP, as per user's actual usage)
    event_json = json.dumps(event, separators=(',', ':'))  # Compact JSON
    event_bytes = event_json.encode('utf-8')

    print(f"📝 Sending: {len(event_bytes)} bytes as plain text")

    try:
        # Write binary to match binary read in send_file()
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as temp_file:
            temp_file.write(event_bytes)
            temp_filename = temp_file.name

        success, result_msg = hsmodem_client.send_file(temp_filename, quiet=True)
        os.unlink(temp_filename)

        if success:
            print(f"✅ Sent plain text via TYPE_IMAGE (uncompressed)")
            last_message_time = current_time

            # Send DM warning if balance is low (AFTER successful send)
            dm_config = config.get('dm_notifications', {})
            if dm_config.get('enabled', False):
                critical_threshold = dm_config.get('critical_balance_threshold_sats', 10)
                low_threshold = dm_config.get('low_balance_threshold_sats', 100)
                sent_notifications = dm_config.get('sent_notifications', {})

                # Critical balance warning
                if new_balance <= critical_threshold and npub not in sent_notifications.get('critical', []):
                    msg = dm_config['critical_balance_message'].format(
                        balance=new_balance,
                        messages=new_balance // price_per_msg if price_per_msg > 0 else 0
                    )
                    if nostr_bot.send_encrypted_dm(npub, msg):
                        if 'critical' not in sent_notifications:
                            sent_notifications['critical'] = []
                        sent_notifications['critical'].append(npub)
                        print(f"📨 Critical balance DM sent to {npub[:16]}...")

                # Low balance warning
                elif new_balance <= low_threshold and npub not in sent_notifications.get('low', []):
                    msg = dm_config['low_balance_message'].format(
                        balance=new_balance,
                        messages=new_balance // price_per_msg if price_per_msg > 0 else 0
                    )
                    if nostr_bot.send_encrypted_dm(npub, msg):
                        if 'low' not in sent_notifications:
                            sent_notifications['low'] = []
                        sent_notifications['low'].append(npub)
                        print(f"📨 Low balance DM sent to {npub[:16]}...")

        else:
            print(f"❌ Satellite failed: {result_msg}")

    except Exception as e:
        print(f"❌ Error: {e}")


async def bridge_mode(config):
    """Nostr to HSModem bridge with payment verification"""
    print("BitSatRelay - Bitcoin Satellite Relay")
    print("=" * 50)

    # Initialize BitSatCredit extension client
    extension_url = config['bitsatcredit_extension']['url']
    credit_client = BitSatCreditClient(extension_url)

    # Health check
    if not credit_client.health_check():
        print(f"❌ BitSatCredit extension not accessible at {extension_url}")
        print("Please ensure LNbits and BitSatCredit extension are running")
        sys.exit(1)

    print(f"✅ BitSatCredit extension connected: {extension_url}")

    # Initialize Nostr bot
    nostr_config = config['nostr']
    nostr_bot = NostrBot(
        nostr_config['bot_nsec'],
        nostr_config['relay_urls']
    )

    # Initialize HSModem
    hsmodem_config = config['hsmodem']
    hsmodem_client = HSModemFileTransfer(
        host=hsmodem_config['host'],
        port=hsmodem_config['port']
    )

    print(f"\nMonitoring relay: {nostr_config['monitor_relay']}")
    print(f"Payment required: {config['pricing']['price_per_message_sats']} sats per message")
    print(f"Top-up page: {extension_url}")
    print("\nStarting bridge...")
    await asyncio.sleep(2)

    relay_url = nostr_config['monitor_relay']

    while True:
        try:
            async with websockets.connect(relay_url) as websocket:
                subscribe_msg = json.dumps([
                    "REQ",
                    "satellite_bridge",
                    {"kinds": [1, 6], "since": int(time.time())}
                ])
                await websocket.send(subscribe_msg)
                print("✅ Connected to relay - waiting for messages (kind 1: notes, kind 6: reposts)...")

                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data[0] == "EVENT":
                            event = data[2]
                            await handle_nostr_event(
                                event,
                                hsmodem_client,
                                credit_client,
                                nostr_bot,
                                config
                            )
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
                    except Exception as e:
                        print(f"Error processing event: {e}")

        except Exception as e:
            print(f"Connection error: {e}")
            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


async def satellite_monitor_mode(config):
    """Start satellite inbound monitoring"""
    print("\nSatellite Monitor - Inbound Message Processing")
    print("=" * 50)

    # Startup delay to allow outbound bridge to establish connections first
    startup_delay = config['satellite_monitor'].get('startup_delay_seconds', 5)
    if startup_delay > 0:
        print(f"⏳ Waiting {startup_delay}s for outbound system to initialize...")
        await asyncio.sleep(startup_delay)
        print("✅ Starting satellite monitor")

    # Initialize Nostr bot
    nostr_config = config['nostr']
    nostr_bot = NostrBot(
        nostr_config['bot_nsec'],
        nostr_config['relay_urls']
    )

    # Initialize satellite monitor
    monitor_config = config['satellite_monitor']
    satellite_monitor = SatelliteMonitor(
        oscar_path=monitor_config['oscar_data_path'],
        processed_path=monitor_config['processed_archive_path'],
        nostr_bot=nostr_bot,
        config=monitor_config
    )

    # Start monitoring
    await satellite_monitor.start_monitoring()


async def dm_bot_mode(config):
    """Run DM bot for interactive commands"""
    dm_bot = DMBot(config)
    await dm_bot.monitor_dms()


async def run_both_systems(config):
    """Run outbound bridge, inbound monitor, and DM bot in parallel"""
    print("BitSatRelay - Two-Way Satellite Communication + DM Bot")
    print("=" * 60)
    print("🚀 Starting outbound bridge (Nostr → Satellite)")
    print("=" * 60)

    # Start outbound bridge first
    bridge_task = asyncio.create_task(bridge_mode(config))

    # Wait 2 seconds for outbound connections to establish
    await asyncio.sleep(2)

    print("\n📡 Starting inbound monitor (Satellite → Nostr)")
    print("=" * 60)

    # Then start inbound monitor
    monitor_task = asyncio.create_task(satellite_monitor_mode(config))

    # Wait 1 second
    await asyncio.sleep(1)

    # Start DM bot if enabled
    dm_task = None
    if config.get('dm_notifications', {}).get('enabled', False):
        print("\n💬 Starting DM Bot (Interactive Commands)")
        print("=" * 60)
        dm_task = asyncio.create_task(dm_bot_mode(config))

    # Run all systems in parallel
    try:
        if dm_task:
            await asyncio.gather(bridge_task, monitor_task, dm_task)
        else:
            await asyncio.gather(bridge_task, monitor_task)
    except asyncio.CancelledError:
        print("\n⏹️ Shutting down all systems...")


def main():
    print("BitSatRelay - Bitcoin Satellite Communication")
    print("=" * 50)

    # Load configuration
    config = load_config()

    # Start both outbound and inbound systems
    try:
        asyncio.run(run_both_systems(config))
    except KeyboardInterrupt:
        print("\n\nBitSatRelay stopped")


if __name__ == "__main__":
    main()