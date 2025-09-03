#!/usr/bin/env python3
"""
BitChat-QO100 Satellite Bridge
Monitors Nostr relay for messages and forwards to HSModem via external interface
"""

import asyncio
import websockets
import json
import socket
import time
from datetime import datetime

# Configuration
RELAY_URL = "ws://localhost:7777"
HSMODEM_IP = "192.168.1.112"
HSMODEM_PORT = 40135
HSMODEM_ID = 0x7743fa9f
MESSAGE_TYPE = 3  # ASCII File

async def bridge_main():
    print("BitChat-QO100 Satellite Bridge")
    print("=" * 40)
    print(f"Relay: {RELAY_URL}")
    print(f"HSModem: {HSMODEM_IP}:{HSMODEM_PORT}")
    print()
    
    if not test_hsmodem_connection():
        print("HSModem connection failed - check configuration")
        return
    
    while True:
        try:
            async with websockets.connect(RELAY_URL) as websocket:
                subscribe_msg = json.dumps([
                    "REQ", 
                    "satellite_bridge",
                    {"kinds": [1], "since": int(time.time())}
                ])
                await websocket.send(subscribe_msg)
                print("Connected to relay, monitoring events...")
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data[0] == "EVENT":
                            event = data[2]
                            await handle_event(event)
                    except (json.JSONDecodeError, Exception) as e:
                        continue
                        
        except Exception as e:
            print(f"Connection error: {e}")
            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

def test_hsmodem_connection():
    """Test UDP connectivity to HSModem"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        
        test_packet = bytearray(224)
        test_packet[0:4] = HSMODEM_ID.to_bytes(4, byteorder='little')
        test_packet[4] = MESSAGE_TYPE
        test_packet[5] = 3
        test_msg = b"CONNECTION TEST"
        test_packet[6:6+len(test_msg)] = test_msg
        
        sock.sendto(bytes(test_packet), (HSMODEM_IP, HSMODEM_PORT))
        print("HSModem connection test successful")
        return True
        
    except Exception as e:
        print(f"HSModem connection test failed: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass

async def handle_event(event):
    """Process Nostr event and forward to satellite"""
    content = event.get('content', '').strip()
    if not content:
        return
        
    author = event.get('pubkey', '')[:8]
    created_at = event.get('created_at', int(time.time()))
    timestamp = datetime.fromtimestamp(created_at).strftime('%H%M')
    
    print(f"New event from {author}: {content[:40]}...")
    
    satellite_msg = f"BITCHAT {author} {timestamp}Z: {content}"
    
    # Limit message length
    max_length = 200
    if len(satellite_msg) > max_length:
        satellite_msg = satellite_msg[:max_length-3] + "..."
    
    if send_to_hsmodem_external(satellite_msg):
        print("Forwarded to QO-100 satellite")
    else:
        print("Failed to send to HSModem")

def send_to_hsmodem_external(message):
    """Send message to HSModem external interface using Type 3 (ASCII File)"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        message_bytes = message.encode('ascii', errors='replace')
        
        if len(message_bytes) <= 200:
            packet = bytearray(224)
            packet[0:4] = HSMODEM_ID.to_bytes(4, byteorder='little')
            packet[4] = MESSAGE_TYPE
            packet[5] = 3  # Single frame
            
            content_length = min(len(message_bytes), 218)
            packet[6:6+content_length] = message_bytes[:content_length]
            
            sock.sendto(bytes(packet), (HSMODEM_IP, HSMODEM_PORT))
            time.sleep(0.1)
            return True
        else:
            print(f"Message too long ({len(message_bytes)} bytes)")
            return False
        
    except Exception as e:
        print(f"HSModem send error: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(bridge_main())
    except KeyboardInterrupt:
        print("\nSatellite bridge stopped")
    except Exception as e:
        print(f"Bridge error: {e}")