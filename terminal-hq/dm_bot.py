#!/usr/bin/env python3
"""
Interactive DM Bot for BitSatRelay
Handles balance inquiries, invoice generation, and help requests via Nostr DMs
"""

import asyncio
import json
import time
import sys
import websockets
from pathlib import Path
from nostr_bot import NostrBot
from bitsatcredit_client import BitSatCreditClient


class DMBot:
    def __init__(self, config):
        """Initialize DM bot with config"""
        self.config = config

        # Initialize Nostr bot for sending DMs
        nostr_config = config['nostr']
        self.nostr_bot = NostrBot(
            nostr_config['bot_nsec'],
            nostr_config['relay_urls']
        )

        # Initialize credit client
        self.credit_client = BitSatCreditClient(
            config['bitsatcredit_extension']['url']
        )

        # Bot's pubkey (for filtering DMs)
        from nostr.key import PrivateKey
        private_key = PrivateKey.from_nsec(nostr_config['bot_nsec'])
        self.private_key = private_key
        self.bot_pubkey = private_key.public_key.hex()

        # Rate limiting: Track last DM time per user
        self.last_dm_time = {}  # {npub: timestamp}
        self.dm_rate_limit = 5.0  # Minimum seconds between DMs from same user

        # Track processed DM event IDs to prevent duplicate responses
        self.processed_dm_ids = set()

        print(f"✅ DM Bot initialized")
        print(f"   Bot pubkey: {self.bot_pubkey[:16]}...")
        print(f"   Rate limit: {self.dm_rate_limit}s per user")

    def decrypt_dm(self, encrypted_content, sender_pubkey_hex):
        """Decrypt NIP-04 encrypted DM content"""
        try:
            import base64
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend

            # Skip empty or malformed content
            if not encrypted_content or len(encrypted_content) < 20:
                print(f"⚠️ DM content too short: {len(encrypted_content) if encrypted_content else 0} chars")
                return None

            # Check for ?iv= separator format (some clients use this)
            if "?iv=" in encrypted_content:
                parts = encrypted_content.split("?iv=")
                if len(parts) == 2:
                    ciphertext = base64.b64decode(parts[0])
                    iv = base64.b64decode(parts[1])
                else:
                    print(f"⚠️ Invalid ?iv= format")
                    return None
            else:
                # Standard format: IV+ciphertext concatenated
                try:
                    decoded = base64.b64decode(encrypted_content)
                except Exception as e:
                    print(f"⚠️ Base64 decode failed: {e}")
                    return None

                # Validate minimum length (16 byte IV + at least 16 byte ciphertext)
                if len(decoded) < 32:
                    print(f"⚠️ Decoded content too short: {len(decoded)} bytes")
                    return None

                # Extract IV (first 16 bytes) and ciphertext
                iv = decoded[:16]
                ciphertext = decoded[16:]

            # Get shared secret using ECDH with nostr library
            shared_secret = self.private_key.compute_shared_secret(sender_pubkey_hex)

            # Decrypt using AES-256-CBC
            cipher = Cipher(
                algorithms.AES(shared_secret),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()

            # Remove PKCS7 padding
            if len(plaintext) == 0:
                print(f"⚠️ Plaintext is empty after decryption")
                return None
            padding_length = plaintext[-1]
            if padding_length > len(plaintext) or padding_length > 16:
                print(f"⚠️ Invalid padding: {padding_length}")
                return None
            plaintext = plaintext[:-padding_length]

            return plaintext.decode('utf-8')

        except Exception as e:
            print(f"❌ Decryption error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_ascii_qr(self, invoice_string):
        """Generate ASCII QR code from invoice string"""
        try:
            import qrcode

            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=1,
            )
            qr.add_data(invoice_string)
            qr.make(fit=True)

            # Render as ASCII
            qr_ascii = qr.get_matrix()
            ascii_output = []

            for row in qr_ascii:
                line = ""
                for cell in row:
                    line += "██" if cell else "  "
                ascii_output.append(line)

            return "\n".join(ascii_output)

        except ImportError:
            return "[QR code generation requires 'qrcode' library]"
        except Exception as e:
            return f"[Error generating QR: {e}]"

    def handle_balance_command(self, sender_npub):
        """Handle /balance command"""
        user = self.credit_client.get_user(sender_npub)

        if not user:
            return (
                "ℹ️ No Account Found\n\n"
                "You don't have an account yet.\n\n"
                "Top up to create your account:\n"
                f"{self.config['bitsatcredit_extension']['url']}/public\n\n"
                "Or send me '/topup' to get a Lightning invoice."
            )

        price_per_msg = self.config['pricing']['price_per_message_sats']
        messages_remaining = user['balance_sats'] // price_per_msg

        return (
            f"💰 BitSatRelay Balance\n\n"
            f"Balance: {user['balance_sats']} sats\n"
            f"Messages remaining: ~{messages_remaining}\n\n"
            f"Total deposited: {user['total_deposited']} sats\n"
            f"Total spent: {user['total_spent']} sats\n"
            f"Messages sent: {user['message_count']}\n\n"
            f"Need more credits? Send '/topup'"
        )

    def handle_topup_command(self, sender_npub, amount_str=None):
        """Handle /topup command - ask for amount or use provided amount"""

        # If no amount provided, ask user to specify
        if not amount_str:
            dm_config = self.config.get('dm_notifications', {})
            suggested_amount = dm_config.get('topup_default_amount_sats', 10000)
            min_amount = self.config.get('pricing', {}).get('min_topup_amount_sats', 10)

            return (
                f"⚡ Top Up Your Account\n\n"
                f"Please specify an amount in sats.\n\n"
                f"Examples:\n"
                f"• /topup 1000 - Add 1,000 sats\n"
                f"• /topup 10000 - Add 10,000 sats\n"
                f"• /topup 100000 - Add 100,000 sats\n\n"
                f"Suggested: {suggested_amount:,} sats\n"
                f"Minimum: {min_amount} sats\n\n"
                f"Or visit the web interface:\n"
                f"{self.config['bitsatcredit_extension']['url']}/public"
            )

        # Parse amount
        try:
            amount_sats = int(amount_str)
            min_amount = self.config.get('pricing', {}).get('min_topup_amount_sats', 10)

            if amount_sats < min_amount:
                return (
                    f"❌ Amount Too Low\n\n"
                    f"Minimum top-up: {min_amount} sats\n"
                    f"You requested: {amount_sats} sats\n\n"
                    f"Try again with a larger amount."
                )

            if amount_sats > 1000000:  # Max 1M sats safety check
                return (
                    f"❌ Amount Too High\n\n"
                    f"Maximum top-up: 1,000,000 sats\n"
                    f"You requested: {amount_sats:,} sats\n\n"
                    f"Try a smaller amount or contact support."
                )

        except ValueError:
            return (
                f"❌ Invalid Amount\n\n"
                f"'{amount_str}' is not a valid number.\n\n"
                f"Examples:\n"
                f"• /topup 1000\n"
                f"• /topup 10000\n\n"
                f"Try again with a number."
            )

        # Generate Lightning invoice via API
        invoice_data = self.credit_client.create_invoice(sender_npub, amount_sats)

        if not invoice_data or 'bolt11' not in invoice_data:
            # Fallback to web link if invoice generation fails
            return (
                f"❌ Invoice Generation Failed\n\n"
                f"Please visit the web interface:\n"
                f"https://lnbits.molonlabe.holdings/bitsatcredit/6e1faaf6356b43029124fdeb5f93a297\n\n"
                f"Or try again later."
            )

        payment_request = invoice_data['bolt11']

        return (
            f"⚡ BitSatRelay Invoice\n\n"
            f"Amount: {amount_sats:,} sats\n\n"
            f"Pay this Lightning invoice:\n\n"
            f"{payment_request}\n\n"
            f"Your balance will update automatically when paid.\n\n"
            f"💡 Scan QR code or copy invoice to your Lightning wallet"
        )

    def handle_help_command(self, sender_npub):
        """Handle /help command"""
        user = self.credit_client.get_user(sender_npub)
        balance_str = f"{user['balance_sats']} sats" if user else "No account"

        return (
            f"🛰️ BitSatRelay Bot - Help\n\n"
            f"I manage your satellite messaging credits.\n\n"
            f"Commands:\n"
            f"/help - Show this message\n"
            f"/balance - Check your balance\n"
            f"/topup <amount> - Top up with specified sats\n"
            f"  Example: /topup 5000\n\n"
            f"Current balance: {balance_str}\n\n"
            f"How it works:\n"
            f"• Pay with Bitcoin Lightning\n"
            f"• Credits added instantly\n"
            f"• Send Nostr messages via satellite\n"
            f"• Off-grid relay for censorship-resistant communication"
        )

    def handle_unknown_message(self, sender_npub):
        """Handle any unrecognized message - send intro with balance if they have account"""
        user = self.credit_client.get_user(sender_npub)

        if user:
            # Existing user - show welcome with their balance
            price_per_msg = self.config['pricing']['price_per_message_sats']
            messages_remaining = user['balance_sats'] // price_per_msg

            return (
                f"👋 Hi! I'm BitSatRelay Bot\n\n"
                f"Your current balance: {user['balance_sats']} sats (~{messages_remaining} messages)\n\n"
                f"Commands:\n"
                f"/help - Show help\n"
                f"/balance - Detailed balance info\n"
                f"/topup <amount> - Add credits (e.g., /topup 5000)\n\n"
                f"Type '/help' for more info."
            )
        else:
            # New user - generic welcome
            return (
                f"👋 Hi! I'm BitSatRelay Bot\n\n"
                f"I manage your satellite messaging credits.\n\n"
                f"You don't have an account yet. Top up to get started:\n"
                f"{self.config['bitsatcredit_extension']['url']}/public\n\n"
                f"Commands:\n"
                f"/help - Show help\n"
                f"/topup <amount> - Add credits (e.g., /topup 5000)\n\n"
                f"Type '/help' for more info."
            )

    def process_dm(self, dm_content, sender_pubkey):
        """Process incoming DM and return response"""
        # Convert sender pubkey to npub
        try:
            from nostr.key import PublicKey
            sender_npub = PublicKey(bytes.fromhex(sender_pubkey)).bech32()
        except:
            sender_npub = f"npub:{sender_pubkey[:16]}..."

        # Parse command and arguments
        parts = dm_content.strip().split()
        command = parts[0].lower() if parts else ""
        args = parts[1:] if len(parts) > 1 else []

        print(f"📩 DM from {sender_npub[:16]}...: {dm_content[:30]}")

        # Route to handler
        if command == "/balance" or command == "balance":
            response = self.handle_balance_command(sender_npub)
        elif command == "/topup" or command == "topup":
            # Pass amount if provided: /topup 5000
            amount_str = args[0] if args else None
            response = self.handle_topup_command(sender_npub, amount_str)
        elif command == "/help" or command == "help":
            response = self.handle_help_command(sender_npub)
        else:
            # Unknown command - send intro
            response = self.handle_unknown_message(sender_npub)

        return response, sender_npub

    async def monitor_single_relay(self, relay_url):
        """Monitor a single relay for DMs"""
        while True:
            try:
                async with websockets.connect(relay_url) as websocket:
                    # Subscribe to kind 4 DMs sent to bot
                    # Use limit: 0 to only get NEW DMs (no historical messages)
                    subscribe_msg = json.dumps([
                        "REQ",
                        "dm_monitor",
                        {
                            "kinds": [4],  # Encrypted DMs
                            "#p": [self.bot_pubkey],  # Tagged to bot
                            "limit": 0  # Only new DMs, not historical
                        }
                    ])
                    await websocket.send(subscribe_msg)
                    print(f"✅ [{relay_url}] Subscribed to DMs (new only)")

                    # Process incoming DMs
                    async for message in websocket:
                        try:
                            data = json.loads(message)

                            # Check if it's an EVENT message
                            if data[0] == "EVENT" and len(data) > 2:
                                event = data[2]

                                # Extract event details
                                event_id = event.get('id', '')
                                sender_pubkey = event.get('pubkey', '')
                                dm_content = event.get('content', '')

                                # Skip if already processed
                                if event_id in self.processed_dm_ids:
                                    continue

                                # Skip if from bot itself
                                if sender_pubkey == self.bot_pubkey:
                                    continue

                                # Convert sender pubkey to npub for rate limiting check
                                try:
                                    from nostr.key import PublicKey
                                    sender_npub_check = PublicKey(bytes.fromhex(sender_pubkey)).bech32()
                                except:
                                    sender_npub_check = f"npub:{sender_pubkey[:16]}..."

                                # Rate limiting: Check if user is sending too fast
                                current_time = time.time()
                                if sender_npub_check in self.last_dm_time:
                                    time_since_last = current_time - self.last_dm_time[sender_npub_check]
                                    if time_since_last < self.dm_rate_limit:
                                        print(f"⏱️ Rate limited: {sender_npub_check[:16]}... ({time_since_last:.1f}s since last DM)")
                                        continue  # Skip this DM, don't respond

                                # Update last DM time for this user
                                self.last_dm_time[sender_npub_check] = current_time

                                # Decrypt DM content (NIP-04)
                                decrypted_content = self.decrypt_dm(dm_content, sender_pubkey)
                                if not decrypted_content:
                                    print(f"⚠️ Could not decrypt DM from {sender_npub_check[:16]}...")
                                    continue

                                # Process DM and generate response
                                response, sender_npub = self.process_dm(decrypted_content, sender_pubkey)

                                # Send response
                                if response:
                                    self.nostr_bot.send_encrypted_dm(sender_npub, response)
                                    print(f"✅ Response sent to {sender_npub[:16]}...")

                                # Mark as processed
                                self.processed_dm_ids.add(event_id)

                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
                        except Exception as e:
                            print(f"Error processing DM: {e}")

            except Exception as e:
                print(f"❌ [{relay_url}] Connection error: {e}")
                print(f"   Reconnecting in 5 seconds...")
                await asyncio.sleep(5)

    async def monitor_dms(self):
        """Monitor all relays for DMs sent to bot"""
        relay_urls = self.config['nostr']['relay_urls']

        print(f"\n📬 DM Bot - Monitoring for incoming messages")
        print(f"   Bot pubkey: {self.bot_pubkey}")
        print(f"   Monitoring {len(relay_urls)} relays:")
        for relay in relay_urls:
            print(f"   • {relay}")
        print()

        # Create tasks for all relays
        tasks = [self.monitor_single_relay(relay) for relay in relay_urls]

        # Run all relay monitors in parallel
        await asyncio.gather(*tasks)


async def main():
    """Main entry point"""
    # Load config
    config_path = Path(__file__).parent / "relay_config.json"

    try:
        with open(config_path) as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)

    # Start DM bot
    bot = DMBot(config)
    await bot.monitor_dms()


if __name__ == "__main__":
    print("=" * 50)
    print("BitSatRelay DM Bot")
    print("=" * 50)
    asyncio.run(main())
