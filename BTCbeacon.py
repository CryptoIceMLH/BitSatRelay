#!/usr/bin/env python3
"""
Bitcoin Beacon - External Data Interface
Uses port 40135 (external data) not 40132 (GUI data)
Requires GUI running with External Application enabled
"""

import socket
import time
import requests
import struct
from datetime import datetime

# HSModem server details
HSMODEM_IP = "192.168.1.112"
EXTERNAL_DATA_PORT = 40135  # External data interface port

def get_live_bitcoin_data():
    """
    Fetch live Bitcoin data from mempool.space API
    Returns formatted message string
    """
    try:
        print("Fetching live Bitcoin data...")
        
        # Get block height
        block_response = requests.get("https://mempool.space/api/blocks/tip/height", timeout=10)
        block_height = block_response.text.strip()
        
        # Get USD price
        price_response = requests.get("https://mempool.space/api/v1/prices", timeout=10)
        price_data = price_response.json()
        usd_price = int(price_data.get('USD', 0))
        
        # Get current UTC time
        utc_time = datetime.utcnow().strftime('%H%M')
        
        # Create beacon message
        message = f"BTC BLOCK {block_height} PRICE {usd_price}USD {utc_time}Z SATOSHI"
        
        print(f"✓ Data fetched: {message}")
        return message
        
    except Exception as e:
        print(f"✗ Error fetching Bitcoin data: {e}")
        utc_time = datetime.utcnow().strftime('%H%M')
        return f"BTC BEACON OFFLINE {utc_time}Z SATOSHI"

def send_external_data(message):
    """
    Send data via External Data Interface (port 40135)
    Correct format from source code:
    - Bytes 0-3: 32-bit ID (0x7743fa9f)
    - Byte 4: Data Type (255 for experimental)
    - Byte 5: Length of data field
    - Bytes 6+: Data (max 217 bytes)
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Prepare message data (HSModem expects total data to be 219 bytes)
        # The data portion should be 219 bytes, but packet has ID+type+length prefix
        message_bytes = message.encode('ascii')
        
        # The data field should be exactly 219 bytes
        # But we need to account for the 6-byte header (4 ID + 1 type + 1 length)
        # So actual data should be 219 - 6 = 213 bytes
        max_data_size = 213
        
        if len(message_bytes) > max_data_size:
            message_bytes = message_bytes[:max_data_size]  # Truncate if too long
        else:
            message_bytes = message_bytes.ljust(max_data_size, b' ')  # Pad with spaces
        
        data_length = len(message_bytes)  # Should be 213
        
        # Create packet: 4 bytes ID + 1 byte type + 1 byte length + data
        packet_size = 4 + 1 + 1 + data_length
        packet = bytearray(packet_size)
        
        # Bytes 0-3: 32-bit ID - HSModem default: 0x7743fa9f
        packet[0] = 0x77
        packet[1] = 0x43  
        packet[2] = 0xfa
        packet[3] = 0x9f
        
        # Byte 4: Data Type (0 = DX cluster message - ASCII text)
        packet[4] = 0
        
        # Byte 5: Length of data field
        packet[5] = data_length
        
        # Bytes 6+: Message data
        packet[6:6+data_length] = message_bytes
        
        # Send to external data port
        sock.sendto(bytes(packet), (HSMODEM_IP, EXTERNAL_DATA_PORT))
        
        print(f"✓ External data sent: {message}")
        print(f"  Packet length: {len(packet)} bytes")
        print(f"  ID: 0x7743fa9f, Type: 0 (DX cluster), Data length: {data_length}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error sending external data: {e}")
        return False
    finally:
        sock.close()

def main():
    print("Bitcoin Beacon - External Data Interface")
    print("=" * 50)
    print(f"Target HSModem: {HSMODEM_IP}")
    print(f"External Data Port: {EXTERNAL_DATA_PORT}")
    print("Live Bitcoin data every 21 seconds")
    print("Data source: mempool.space API")
    print("Beacon ID: SATOSHI")
    print()
    print("REQUIREMENTS:")
    print("1. HSModem GUI must be running")
    print("2. 'External Application' must be enabled in GUI")
    print("3. External data interface must be active")
    print()
    print("Press Ctrl+C to stop")
    print()
    
    transmission_count = 0
    
    try:
        while True:
            transmission_count += 1
            print(f"--- External Data Transmission #{transmission_count} ---")
            
            # Get Bitcoin data
            bitcoin_message = get_live_bitcoin_data()
            
            # Send via external data interface
            send_external_data(bitcoin_message)
            
            # Wait 21 seconds for next transmission
            print("Next beacon in 21 seconds...")
            print()
            time.sleep(21)
            
    except KeyboardInterrupt:
        print(f"\nBeacon stopped. Total transmissions: {transmission_count}")

if __name__ == "__main__":
    main()