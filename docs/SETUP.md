# BitSatRelay Setup Guide

Complete installation and configuration guide for deploying your own Terminal-HQ.

---

## Prerequisites

### Hardware Requirements
- **Server**: Ubuntu 20.04+ Linux server (2+ cores, 4GB RAM, 20GB SSD)
- **Satellite Modem**: HSModem or compatible device
- **Uplink**: 2.4 GHz transmitter (13cm amateur band)
- **Downlink**: 10.489 GHz receiver (Ku band)
- **Satellite Dish**: Appropriate feed for both bands
- **Internet**: Stable connection (fiber/cellular)

### Software Requirements
- Python 3.8+
- LNbits instance with BitSatCredit extension installed
- Oscar software for satellite RX decoding
- Network access to HSModem (TCP/IP)

---

## Step 1: Clone Repository

```bash
git clone https://github.com/CryptoIceMLH/BitSatRelay.git
cd BitSatRelay/terminal-hq
```

---

## Step 2: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip git -y

# Install Python dependencies
pip3 install -r requirements.txt
```

---

## Step 3: Generate Nostr Keys

You need a Nostr keypair for your bot identity.

**Option A: Use existing Nostr client**
- Generate keys in Damus, Amethyst, or any Nostr client
- Export the nsec (private key) and npub (public key)

**Option B: Generate keys programmatically**
```python
from nostr.key import PrivateKey

private_key = PrivateKey()
public_key = private_key.public_key

print(f"nsec: {private_key.bech32()}")
print(f"npub: {public_key.bech32()}")
```

**IMPORTANT**: Keep your nsec secret! Never commit it to git.

---

## Step 4: Configure LNbits + BitSatCredit Extension

1. **Deploy LNbits**:
   - Self-hosted: https://github.com/lnbits/lnbits
   - Umbrel: Install from App Store
   - Cloud: Use hosted LNbits service

2. **Install BitSatCredit Extension**:
   - Navigate to LNbits Extensions
   - Install BitSatCredit extension (separate repository)
   - Create a wallet for BitSatCredit
   - Note the wallet ID (you'll need this)

3. **Get API URL**:
   - Your BitSatCredit API URL: `https://your-lnbits.com/bitsatcredit`

---

## Step 5: Configure HSModem

1. **Connect HSModem**:
   - Connect modem to your network via Ethernet
   - Note the IP address (e.g., `192.168.1.112`)
   - Default port: `40132`

2. **Test Connectivity**:
```bash
nc -zv 192.168.1.112 40132
```

---

## Step 6: Setup Local Nostr Relay (strfry)

BitSatRelay uses a local strfry relay to monitor incoming satellite messages. This relay runs on `ws://localhost:7777` and allows clients to connect via WebSocket.

### Install strfry

```bash
# Install dependencies
sudo apt install -y git build-essential pkg-config libtool autoconf automake \
  liblmdb-dev libsecp256k1-dev libzstd-dev libb2-dev flatbuffers-compiler

# Clone strfry
cd /opt
sudo git clone https://github.com/hoytech/strfry.git
cd strfry

# Build strfry
sudo git submodule update --init
sudo make setup-golpe
sudo make -j$(nproc)

# Install
sudo cp strfry /usr/local/bin/
```

### Configure strfry

Create config file:
```bash
sudo mkdir -p /etc/strfry
sudo nano /etc/strfry/strfry.conf
```

Basic configuration:
```conf
##
## Default strfry config
##

db = "/var/lib/strfry/"

dbParams {
    # Maximum number of threads/processes that can simultaneously have LMDB transactions open (restart required)
    maxreaders = 256

    # Size of mmap() to use when loading LMDB (default is 10TB, restart required)
    dbsize = 10737418240
}

events {
    # Maximum size of normalised JSON, in bytes
    maxEventSize = 65536

    # Events newer than this will be rejected
    rejectEventsNewerThanSeconds = 900

    # Events older than this will be rejected
    rejectEventsOlderThanSeconds = 94608000

    # Ephemeral events older than this will be rejected
    rejectEphemeralEventsOlderThanSeconds = 60

    # Ephemeral events will be deleted from the DB when older than this
    ephemeralEventsLifetimeSeconds = 300

    # Maximum number of tags allowed
    maxNumTags = 2000

    # Maximum size for tag values, in bytes
    maxTagValSize = 1024
}

relay {
    # Interface to listen on. Use 0.0.0.0 to listen on all interfaces (restart required)
    bind = "127.0.0.1"

    # Port to open for the WebSocket protocol (restart required)
    port = 7777

    # Set OS-limit on maximum number of open files/sockets (if 0, don't attempt to set) (restart required)
    nofiles = 1000000

    # HTTP header that contains the client's real IP, before reverse proxying (ie x-real-ip) (MUST be all lower-case)
    realIpHeader = ""

    info {
        # NIP-11: Name of this server. Short/descriptive (< 30 characters)
        name = "BitSatRelay Monitor"

        # NIP-11: Detailed information about relay, free-form
        description = "Local relay for BitSatRelay satellite bridge monitoring"

        # NIP-11: Public key for relay operator
        pubkey = ""

        # NIP-11: Alternative administrative contact
        contact = ""
    }

    # Maximum accepted incoming websocket frame size (should be larger than max event) (restart required)
    maxWebsocketPayloadSize = 131072

    # Websocket-level PING message frequency (should be less than any reverse proxy idle timeouts) (restart required)
    autoPingSeconds = 55

    # If TCP keep-alive should be enabled (detect dropped connections to upstream reverse proxy)
    enableTcpKeepalive = false

    # How much uninterrupted CPU time a REQ query should get during its DB scan
    queryTimesliceBudgetMicroseconds = 10000

    # Maximum records that can be returned per filter
    maxFilterLimit = 500

    # Maximum number of subscriptions (concurrent REQs) a connection can have open at any time
    maxSubsPerConnection = 20
}
```

Create strfry data directory:
```bash
sudo mkdir -p /var/lib/strfry
sudo chown $USER:$USER /var/lib/strfry
```

### Setup strfry as systemd service

```bash
sudo nano /etc/systemd/system/strfry.service
```

```ini
[Unit]
Description=strfry Nostr Relay
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
ExecStart=/usr/local/bin/strfry relay --config=/etc/strfry/strfry.conf
Restart=always
RestartSec=10
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable strfry
sudo systemctl start strfry
sudo systemctl status strfry
```

### Test Local Relay

```bash
# Install wscat for testing
npm install -g wscat

# Test WebSocket connection
wscat -c ws://localhost:7777

# You should see a connection confirmation
# Type: ["REQ","test",{}]
# Press Ctrl+C to exit
```

### Setup Reverse Proxy (Optional - for external WSS access)

If you want clients to connect from the internet, setup nginx reverse proxy:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx

# Create nginx config
sudo nano /etc/nginx/sites-available/strfry
```

```nginx
# WebSocket upgrade headers
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 80;
    server_name relay.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:7777;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket timeout settings
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

Enable site and get SSL certificate:
```bash
sudo ln -s /etc/nginx/sites-available/strfry /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d relay.yourdomain.com
```

Now clients can connect to: `wss://relay.yourdomain.com`

### Update BitSatRelay Config

Add your local relay to the config:

```json
{
  "nostr": {
    "relay_urls": [
      "wss://relay.damus.io",
      "wss://nos.lol",
      "wss://relay.primal.net"
    ],
    "monitor_relay": "ws://localhost:7777"
  }
}
```

**Important**: The `monitor_relay` is where BitSatRelay posts incoming satellite messages. Public relays in `relay_urls` are for subscribing to outbound messages.

---

## Step 7: Configure Oscar (Satellite RX)

1. **Install Oscar Software**:
   - Follow Oscar installation guide for your satellite modem
   - Configure SMB share for decoded data

2. **Mount Oscar Data Path**:
```bash
# Example: Mount SMB share
sudo mount -t cifs //192.168.1.112/oscardata /mnt/oscardata \
  -o username=YOUR_USER,password=YOUR_PASS
```

3. **Update config with Oscar path**:
   - `oscar_data_path`: Path to RXimages folder
   - `processed_archive_path`: Path to processed files

---

## Step 7: Create Configuration File

```bash
cd terminal-hq
cp relay_config.json.example relay_config.json
nano relay_config.json
```

Update the following fields:

```json
{
  "bitsatcredit_extension": {
    "url": "https://your-lnbits-instance.com/bitsatcredit"
  },
  "nostr": {
    "bot_nsec": "nsec1YOUR_ACTUAL_PRIVATE_KEY",
    "bot_npub": "npub1YOUR_ACTUAL_PUBLIC_KEY",
    "relay_urls": [
      "wss://relay.damus.io",
      "wss://nos.lol",
      "wss://relay.primal.net"
    ]
  },
  "hsmodem": {
    "host": "192.168.1.112",
    "port": 40132
  },
  "satellite_monitor": {
    "oscar_data_path": "/path/to/oscar/RXimages/",
    "processed_archive_path": "/path/to/oscar/RXimages/processed/"
  }
}
```

**CRITICAL**: Set proper file permissions:
```bash
chmod 600 relay_config.json  # Owner read/write only
```

---

## Step 8: Test Configuration

```bash
# Test Nostr connection
python3 -c "from nostr_bot import NostrBot; print('Nostr OK')"

# Test LNbits API
python3 -c "from bitsatcredit_client import BitSatCreditClient; print('LNbits OK')"

# Test HSModem connection
nc -zv 192.168.1.112 40132
```

---

## Step 9: Run BitSatRelay

### Test Run (foreground)
```bash
cd terminal-hq
python3 BitSatRelay.py
```

You should see:
```
🚀 Starting BitSatRelay...
📡 Nostr Bot connected to 4 relays
💬 DM Bot started
🛰️ Satellite monitor started
✅ All systems operational
```

### Production Run (systemd service)

Create service file:
```bash
sudo nano /etc/systemd/system/bitsatrelay.service
```

```ini
[Unit]
Description=BitSatRelay Terminal-HQ
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/BitSatRelay/terminal-hq
ExecStart=/usr/bin/python3 BitSatRelay.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable bitsatrelay
sudo systemctl start bitsatrelay
sudo systemctl status bitsatrelay
```

View logs:
```bash
sudo journalctl -u bitsatrelay -f
```

---

## Step 10: Test End-to-End

### Test Outbound (Nostr → Satellite)

1. **Add credits** to your test npub:
   - DM the bot: `/topup 1000`
   - Pay the Lightning invoice

2. **Post to Nostr**:
   - Use any Nostr client
   - Post a public message
   - Watch Terminal-HQ logs

3. **Verify satellite TX**:
   - Check HSModem logs
   - Message should be transmitted

### Test Inbound (Satellite → Nostr)

1. **Transmit test message** via satellite
2. **Oscar decodes** and writes .txt file
3. **Terminal-HQ detects** new file
4. **Bot posts** to Nostr relays
5. **Verify** message appears on Nostr clients

### Test DM Bot

Send DMs to your bot npub:
- `/help` - Should reply with commands
- `/balance` - Should show your balance
- `/topup 100` - Should generate Lightning invoice

---

## Troubleshooting

### Bot not connecting to Nostr relays
- Check relay URLs are valid
- Test with: `wscat -c wss://relay.damus.io`
- Verify nsec/npub format

### Credit check fails
- Verify LNbits URL is accessible
- Test API: `curl https://your-lnbits.com/bitsatcredit/api/v1/user/{npub}`
- Check BitSatCredit extension is enabled

### Satellite TX not working
- Verify HSModem IP and port
- Test connection: `nc -zv 192.168.1.112 40132`
- Check HSModem logs

### Satellite RX not detected
- Verify Oscar data path is correct
- Check SMB mount: `ls /path/to/oscar/RXimages/`
- Verify file permissions

### DM Bot not responding
- Check bot is decrypting DMs correctly
- Verify NIP-04 encryption working
- Test with known working client (Amethyst, Damus)

---

## Security Best Practices

1. **Never commit relay_config.json** to git
2. **Set file permissions**: `chmod 600 relay_config.json`
3. **Use HTTPS** for LNbits API
4. **Keep nsec secret** - never share or expose
5. **Rate limit** enabled by default (5 sec/msg)
6. **Firewall**: Only expose necessary ports
7. **Backup**: Regular backups of config and LNbits data

---

## Monitoring

### Log Monitoring
```bash
# Watch BitSatRelay logs
sudo journalctl -u bitsatrelay -f

# Watch for errors
sudo journalctl -u bitsatrelay | grep ERROR
```

### Performance Metrics
- **Throughput**: Messages/minute
- **Latency**: Nostr → Satellite delay
- **Uptime**: Service availability
- **Credit usage**: Track via LNbits dashboard

---

## Upgrading

```bash
# Stop service
sudo systemctl stop bitsatrelay

# Pull latest code
cd BitSatRelay
git pull origin main

# Reinstall dependencies (if updated)
pip3 install -r terminal-hq/requirements.txt

# Restart service
sudo systemctl start bitsatrelay
```

---

## Support

- **Nostr**: `npub14uee3fwxjwq7m25gsyqguv2t6v8ft69jax4lvs3skfpa8u7thdsqpu7gam`
- **GitHub Issues**: [Report bugs and request features]
- **Website**: https://bitsat.molonlabe.holdings

---

## License

MIT License - see [LICENSE](../LICENSE) for details
