#!/usr/bin/env python3
"""
Nostr Bot for BitSatRelay
Posts quote messages to Nostr relays when messages are relayed via satellite
"""

import ssl
import time
import json
import socket
import threading
import hashlib
from nostr.event import Event
from nostr.relay_manager import RelayManager
from nostr.key import PrivateKey, PublicKey


def hex_to_note(event_id_hex):
    """Convert hex event ID to note1... bech32 format using NIP-19"""
    try:
        # Use nostr library's built-in conversion
        from nostr.key import PublicKey
        # The PublicKey class can convert any 32-byte hex to bech32
        # Temporarily use it for event IDs too (they're both 32 bytes)
        event_bytes = bytes.fromhex(event_id_hex)

        # Manual bech32 encoding for 'note' prefix
        # Convert bytes to 5-bit groups
        def convertbits(data, frombits, tobits, pad=True):
            acc = 0
            bits = 0
            ret = []
            maxv = (1 << tobits) - 1
            for value in data:
                acc = (acc << frombits) | value
                bits += frombits
                while bits >= tobits:
                    bits -= tobits
                    ret.append((acc >> bits) & maxv)
            if pad and bits:
                ret.append((acc << (tobits - bits)) & maxv)
            return ret

        # Bech32 charset
        CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

        def bech32_polymod(values):
            GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
            chk = 1
            for v in values:
                b = chk >> 25
                chk = (chk & 0x1ffffff) << 5 ^ v
                for i in range(5):
                    chk ^= GEN[i] if ((b >> i) & 1) else 0
            return chk

        def bech32_hrp_expand(hrp):
            return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]

        def bech32_create_checksum(hrp, data):
            values = bech32_hrp_expand(hrp) + data
            polymod = bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
            return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]

        # Encode to bech32
        hrp = "note"
        data = convertbits(event_bytes, 8, 5)
        combined = data + bech32_create_checksum(hrp, data)
        return hrp + '1' + ''.join([CHARSET[d] for d in combined])

    except Exception as e:
        print(f"Warning: Could not convert to note format: {e}")
        # Fallback: return hex as-is - this WON'T work for clients!
        return event_id_hex


class NostrBot:
    def __init__(self, bot_nsec, relay_list):
        """Initialize bot with private key and relay list"""
        try:
            self.private_key = PrivateKey.from_nsec(bot_nsec)
            self.relay_manager = RelayManager()
            self.relay_list = relay_list

            # Add configured relays
            for relay_url in relay_list:
                self.relay_manager.add_relay(relay_url)
                print(f"Added relay: {relay_url}")

            # Open connections
            self.relay_manager.open_connections({"cert_reqs": ssl.CERT_NONE})
            time.sleep(1.25)  # Allow connections to establish

            print(f"✅ Nostr bot initialized with {len(relay_list)} relays")

        except Exception as e:
            print(f"❌ Error initializing Nostr bot: {e}")
            raise

    def fetch_event_by_id(self, event_id):
        """Fetch event content by ID from relay (for showing reply context)"""
        try:
            import websocket

            # Use first relay from list
            relay_url = self.relay_list[0] if self.relay_list else None
            if not relay_url:
                return None

            # Quick fetch with timeout
            ws = websocket.create_connection(relay_url, timeout=3)

            # Request specific event
            req_msg = json.dumps(["REQ", "fetch_preview", {"ids": [event_id]}])
            ws.send(req_msg)

            # Wait for response (max 2 seconds)
            start_time = time.time()
            while time.time() - start_time < 2:
                try:
                    msg = ws.recv()
                    data = json.loads(msg)

                    # Check if it's an EVENT response
                    if data[0] == "EVENT" and len(data) > 2:
                        event = data[2]
                        content = event.get('content', '')[:150]  # Truncate to 150 chars
                        ws.close()
                        return content

                except Exception:
                    break

            ws.close()
            return None

        except Exception as e:
            return None

    def _ensure_connected(self):
        """Ensure relay connections are open, reconnect if needed"""
        try:
            # Try to reconnect if connections are closed
            self.relay_manager.close_connections()
            time.sleep(0.5)
            self.relay_manager.open_connections({"cert_reqs": ssl.CERT_NONE})
            time.sleep(1.25)
            print("🔄 Reconnected to Nostr relays")
        except Exception as e:
            print(f"⚠️ Error reconnecting: {e}")

    def rebroadcast_event(self, event_dict):
        """V4: Rebroadcast original event using raw WebSocket - SYNC version"""
        try:
            import websocket
            import threading
            
            message = json.dumps(["EVENT", event_dict])
            success_count = 0
            
            def send_to_relay(relay_url):
                nonlocal success_count
                try:
                    ws = websocket.create_connection(relay_url, timeout=5)
                    ws.send(message)
                    # Try to receive response
                    try:
                        response = ws.recv(timeout=2)
                        if '"ok"' in response or 'true' in response:
                            success_count += 1
                            print(f"✅ {relay_url} accepted")
                    except:
                        # No response is fine
                        success_count += 1
                        print(f"✅ {relay_url} sent")
                    ws.close()
                except Exception as e:
                    print(f"⚠️ {relay_url}: {e}")
            
            # Send to all relays in parallel threads
            threads = []
            for relay_url in self.relay_list:
                thread = threading.Thread(target=send_to_relay, args=(relay_url,))
                thread.start()
                threads.append(thread)
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=10)
            
            print(f"✅ Rebroadcast to {success_count}/{len(self.relay_list)} relays: {event_dict['id'][:16]}...")
            return event_dict['id']
            
        except Exception as e:
            print(f"❌ Error rebroadcasting: {e}")
            return None

    def create_quote_note(self, event_dict):
        """V4: Create satellite quote note - manual signing via direct WebSocket"""
        try:
            import websocket

            # Handle different event types
            event_kind = event_dict.get('kind', 1)
            original_pubkey = event_dict.get('pubkey', '')
            original_tags = event_dict.get('tags', [])

            # Convert author pubkey to npub for display
            try:
                from nostr.key import PublicKey
                npub = PublicKey(bytes.fromhex(original_pubkey)).bech32()
            except:
                npub = f"npub:{original_pubkey[:16]}..."

            # Initialize context variables
            interaction_type = ""  # "Reply", "Quote", "Repost", or ""
            target_npub = None
            target_event_id = None
            original_content = ""

            # REPOST (kind 6): Extract reposted content and author
            if event_kind == 6:
                try:
                    reposted_event = json.loads(event_dict.get('content', '{}'))
                    reposted_content = reposted_event.get('content', '')
                    reposted_pubkey = reposted_event.get('pubkey', '')

                    # Get reposted author's npub
                    try:
                        target_npub = PublicKey(bytes.fromhex(reposted_pubkey)).bech32()
                    except:
                        target_npub = f"npub:{reposted_pubkey[:16]}..."

                    # Get event ID from 'e' tag
                    for tag in original_tags:
                        if tag[0] == 'e' and len(tag) > 1:
                            target_event_id = tag[1]
                            break

                    interaction_type = "🔁 REPOST"
                    original_content = reposted_content[:200]
                    if len(reposted_content) > 200:
                        original_content += "..."

                except (json.JSONDecodeError, KeyError):
                    interaction_type = "🔁 REPOST"
                    original_content = "[Content unavailable]"

            # QUOTE (kind 1 with 'q' tag): Shows quote context
            elif event_kind == 1:
                # Check for 'q' tag (quote)
                for tag in original_tags:
                    if tag[0] == 'q' and len(tag) > 1:
                        target_event_id = tag[1]
                        interaction_type = "💬 QUOTE"
                        break

                # If not a quote, check for reply
                if not interaction_type:
                    for tag in original_tags:
                        if tag[0] == 'e' and len(tag) > 1:
                            # Check for 'reply' marker (4th element)
                            if len(tag) >= 4 and tag[3] == 'reply':
                                target_event_id = tag[1]
                                interaction_type = "↩️ REPLY"
                                break
                            # Fallback: use last 'e' tag
                            elif target_event_id is None:
                                target_event_id = tag[1]
                                interaction_type = "↩️ REPLY"

                # Get target person from 'p' tags (first one that's not the author)
                if interaction_type in ["↩️ REPLY", "💬 QUOTE"]:
                    for tag in original_tags:
                        if tag[0] == 'p' and len(tag) > 1:
                            reply_pubkey = tag[1]
                            if reply_pubkey != original_pubkey:
                                try:
                                    target_npub = PublicKey(bytes.fromhex(reply_pubkey)).bech32()
                                except:
                                    target_npub = f"npub:{reply_pubkey[:16]}..."
                                break

                # Use content directly for kind 1
                original_content = event_dict.get('content', '')

            # Build context header and message based on interaction type
            if interaction_type == "🔁 REPOST":
                # Repost: "Nikos REPOSTED Nathan's post"
                context_line = f"🔁 nostr:{npub} REPOSTED"
                if target_npub:
                    context_line += f" nostr:{target_npub}'s post\n\n"
                else:
                    context_line += "\n\n"

                message = (
                    f"🛰️Off-Grid Relayed via satellite🛰️\n"
                    f"--------------------------------\n\n"
                    f"{context_line}"
                    f"Original post:\n"
                    f"{original_content}\n\n"
                    f"--------------------------------\n"
                    f"📡 BitSatRelay - Terminal-HQ"
                )

            elif interaction_type == "💬 QUOTE":
                # Quote: Quoted message appears below, no Re: line needed
                context_header = ""
                if target_npub:
                    context_header = f"💬 QUOTE to nostr:{target_npub}\n\n"

                message = (
                    f"🛰️Off-Grid Relayed via satellite🛰️\n"
                    f"--------------------------------\n\n"
                    f"{context_header}"
                    f"nostr:{npub} said:\n"
                    f"{original_content}\n\n"
                    f"--------------------------------\n"
                    f"📡 BitSatRelay - Terminal-HQ"
                )

            elif interaction_type == "↩️ REPLY":
                # Reply: Show Re: line so readers know what's being replied to
                context_header = ""
                if target_npub:
                    context_header = f"↩️ REPLY to nostr:{target_npub}\n"
                    if target_event_id:
                        # Convert hex event ID to note1... format for client linking
                        note_id = hex_to_note(target_event_id)
                        context_header += f"Re: nostr:{note_id}\n"
                    context_header += "\n"

                message = (
                    f"🛰️Off-Grid Relayed via satellite🛰️\n"
                    f"--------------------------------\n\n"
                    f"{context_header}"
                    f"nostr:{npub} said:\n"
                    f"{original_content}\n\n"
                    f"--------------------------------\n"
                    f"📡 BitSatRelay - Terminal-HQ"
                )

            else:
                # Regular post (no interaction)
                message = (
                    f"🛰️Off-Grid Relayed via satellite🛰️\n"
                    f"--------------------------------\n\n"
                    f"nostr:{npub} said:\n"
                    f"{original_content}\n\n"
                    f"--------------------------------\n"
                    f"📡 BitSatRelay - Terminal-HQ"
                )

            # Build tags: include original author + all people tagged in original message
            tags = [
                ['q', event_dict['id']],           # Quote the original event
                ['e', event_dict['id']],           # Reference the original event
                ['p', event_dict['pubkey']]        # Tag the original author (pings them)
            ]

            # Add all 'e' tags from original message (preserves reply chain for threading)
            for tag in original_tags:
                if tag[0] == 'e' and len(tag) > 1:
                    # Don't duplicate the one we already added
                    if tag[1] != event_dict['id']:
                        tags.append(tag)  # Keep full tag (includes relay hints, markers)

            # Add all 'p' tags from original message (pings everyone mentioned)
            for tag in original_tags:
                if tag[0] == 'p' and len(tag) > 1:
                    # Don't duplicate - check if pubkey already tagged
                    pubkey = tag[1]
                    if not any(t[0] == 'p' and len(t) > 1 and t[1] == pubkey for t in tags):
                        tags.append(['p', pubkey])

            # Build event dict with all fields upfront (NIP-01 compliant)
            event = {
                "pubkey": self.private_key.public_key.hex(),
                "created_at": int(time.time()),
                "kind": 1,
                "tags": tags,
                "content": message
            }

            # Compute event ID per NIP-01: SHA256 of serialized array
            # [0, pubkey, created_at, kind, tags, content]
            serialize = json.dumps([
                0,
                event["pubkey"],
                event["created_at"],
                event["kind"],
                event["tags"],
                event["content"]
            ], separators=(',', ':'), ensure_ascii=False)

            event_id = hashlib.sha256(serialize.encode('utf-8')).hexdigest()
            event["id"] = event_id

            # Sign event - convert dict to Event object just for signing
            # Create a minimal Event-like object that sign_event can work with
            class EventForSigning:
                def __init__(self, event_dict):
                    self.id = event_dict["id"]
                    self.public_key = event_dict["pubkey"]
                    self.created_at = event_dict["created_at"]
                    self.kind = event_dict["kind"]
                    self.tags = event_dict["tags"]
                    self.content = event_dict["content"]
                    self.signature = None

            temp_event = EventForSigning(event)
            self.private_key.sign_event(temp_event)
            event["sig"] = temp_event.signature

            print(f"✅ Quote note created: {event_id[:16]}...")

            # Send via direct WebSocket (same as rebroadcast_event)
            message = json.dumps(["EVENT", event])
            success_count = 0

            def send_to_relay(relay_url):
                nonlocal success_count
                try:
                    ws = websocket.create_connection(relay_url, timeout=5)
                    ws.send(message)
                    # Try to receive response
                    try:
                        response = ws.recv(timeout=2)
                        if '"ok"' in response or 'true' in response:
                            success_count += 1
                            print(f"✅ {relay_url} accepted quote")
                    except:
                        # No response is fine
                        success_count += 1
                        print(f"✅ {relay_url} sent quote")
                    ws.close()
                except Exception as e:
                    print(f"⚠️ {relay_url}: {e}")

            # Send to all relays in parallel threads
            threads = []
            for relay_url in self.relay_list:
                thread = threading.Thread(target=send_to_relay, args=(relay_url,))
                thread.start()
                threads.append(thread)

            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=10)

            print(f"✅ Quote note published to {success_count}/{len(self.relay_list)} relays")
            return event_id

        except Exception as e:
            print(f"❌ Error creating quote: {e}")
            import traceback
            traceback.print_exc()
            return None

    def rebroadcast_and_quote(self, event_dict):
        """V4: Main method - rebroadcast original + create quote"""
        try:
            # 1. Rebroadcast original (invisible)
            original_result = self.rebroadcast_event(event_dict)
            # 2. Create quote note (visible)
            quote_result = self.create_quote_note(event_dict)
            
            if original_result or quote_result:
                print("✅ Complete: Rebroadcast + Quote")
                return True
            else:
                print("⚠️ Partial success - some operations failed")
                return False
        except Exception as e:
            print(f"❌ Error in rebroadcast_and_quote: {e}")
            return False

    def send_encrypted_dm(self, recipient_npub, message_text):
        """Send encrypted DM (NIP-04) to user"""
        try:
            import websocket
            from nostr.key import PublicKey
            import base64
            import os
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend

            # Convert npub to hex pubkey
            recipient_pubkey_hex = PublicKey.from_npub(recipient_npub).hex()

            # Encrypt message using NIP-04
            # Get shared secret using nostr library
            shared_secret = self.private_key.compute_shared_secret(recipient_pubkey_hex)

            # Generate random IV (16 bytes)
            iv = os.urandom(16)

            # Add PKCS7 padding
            plaintext = message_text.encode('utf-8')
            padding_length = 16 - (len(plaintext) % 16)
            plaintext += bytes([padding_length]) * padding_length

            # Encrypt using AES-256-CBC
            cipher = Cipher(
                algorithms.AES(shared_secret),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(plaintext) + encryptor.finalize()

            # Use NIP-04 standard format: base64(ciphertext)?iv=base64(iv)
            encrypted_content = base64.b64encode(ciphertext).decode('utf-8') + '?iv=' + base64.b64encode(iv).decode('utf-8')

            # Build DM event (kind 4)
            tags = [
                ['p', recipient_pubkey_hex]  # Recipient
            ]

            # Build event
            event = {
                "pubkey": self.private_key.public_key.hex(),
                "created_at": int(time.time()),
                "kind": 4,  # Encrypted Direct Message
                "tags": tags,
                "content": encrypted_content
            }

            # Compute event ID
            serialize = json.dumps([
                0,
                event["pubkey"],
                event["created_at"],
                event["kind"],
                event["tags"],
                event["content"]
            ], separators=(',', ':'), ensure_ascii=False)

            event_hash = hashlib.sha256(serialize.encode('utf-8')).digest()
            event["id"] = event_hash.hex()

            # Sign event - create wrapper object for signing
            class EventForSigning:
                def __init__(self, event_dict):
                    self.id = event_dict["id"]
                    self.pubkey = event_dict["pubkey"]
                    self.created_at = event_dict["created_at"]
                    self.kind = event_dict["kind"]
                    self.tags = event_dict["tags"]
                    self.content = event_dict["content"]
                    self.signature = None

            temp_event = EventForSigning(event)
            self.private_key.sign_event(temp_event)
            event["sig"] = temp_event.signature

            # Send to first relay
            relay_url = self.relay_list[0] if self.relay_list else None
            if not relay_url:
                print("❌ No relay configured for DM")
                return False

            ws = websocket.create_connection(relay_url, timeout=5)
            event_msg = json.dumps(["EVENT", event])
            ws.send(event_msg)

            # Wait for OK response
            response = ws.recv()
            ws.close()

            print(f"📨 DM sent to {recipient_npub[:16]}...")
            return True

        except Exception as e:
            print(f"❌ Error sending DM: {e}")
            return False

    def close(self):
        """Close relay connections"""
        try:
            self.relay_manager.close_connections()
            print("Nostr bot connections closed")
        except Exception as e:
            print(f"Error closing connections: {e}")


if __name__ == "__main__":
    print("Nostr Bot module loaded successfully!")