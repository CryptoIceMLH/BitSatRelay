# BitSatRelay - Bitcoin Nostr Satellite Communications

**Uncensorable, off-grid communications via satellite**

BitSatRelay bridges the internet-connected Nostr protocol with satellite communications, enabling global messaging that works even when the internet doesn't.

---

## 💜 Support This Project

If you wish to support my work you can donate with BTC:

⚡ **BTC Lightning**: `cryptoice@walletofsatoshi.com`

⚡ **BTC Onchain**: `347ePgUhyvztUWVZ4YZBmBLgTn8hxUFNeQ`

---

> **⚠️ WORK IN PROGRESS**
>
> This repository contains functional code and initial documentation. Additional setup guides are being prepared:
> - HSModem configuration and tuning
> - Nostr strfry relay deployment
> - Network configuration and IP routing
> - Oscar software setup
> - Terminal-1 off-grid kit assembly
>
> Contributions and feedback welcome!

---

## What is BitSatRelay?

BitSatRelay is a complete system for sending and receiving Nostr messages via satellite. It allows users to communicate on the Nostr network without internet access, using only satellite equipment and a small computer.

**Key Features:**
- 🛰️ Send and receive Nostr posts via satellite
- ⚡ Pay-per-message micropayments (Lightning Network)
- 💬 Interactive DM bot for credit management
- 🌍 Works anywhere with satellite coverage
- 🔒 Censorship-resistant communications
- 📡 No internet required for end users

---

## System Architecture

BitSatRelay consists of three main components working together:

### 1. Terminal-HQ (Internet-Connected Bridge)

The heart of the system - a ground station that bridges internet and satellite.

**What it does:**
- Monitors Nostr relays for new posts
- Checks user credits via LNbits API
- Transmits approved messages to satellite
- Receives satellite messages and posts to Nostr
- Manages user accounts via encrypted DMs

**Hardware:**
- Linux server (Ubuntu)
- Custom satellite modem (HSModem)
- Satellite uplink/downlink equipment
- Internet connection

**Software Stack:**
- Python 3.8+
- Nostr protocol (NIP-01, NIP-04, NIP-10, NIP-18, NIP-19)
- LNbits for Lightning payments
- Custom BitSatCredit extension

### 2. BitSatCredit Extension (Credit Management)

A custom LNbits extension that handles the pay-per-message system. **(Separate repository)**

**What it does:**
- Tracks user balances in sats
- Generates Lightning invoices for top-ups
- Deducts credits when messages are sent
- Provides public API for Terminal-HQ

**Key Features:**
- REST API for credit checks and deductions
- Automatic credit addition when invoices are paid
- Transaction history tracking
- Public top-up endpoint (no auth required)
- User invoice generation via DM bot

### 3. DM Bot (User Interface)

An interactive Nostr DM bot that users chat with to manage their accounts.

**Commands:**
- `/balance` - Check current credit balance
- `/topup <amount>` - Generate Lightning invoice to add credits
- `/help` - Show available commands

**What it does:**
- Receives encrypted DMs (NIP-04)
- Checks balances via BitSatCredit API
- Generates Lightning invoices on demand
- Sends low balance warnings automatically
- Rate-limited to prevent spam

---

## How It Works

### Outbound Flow (Internet → Satellite)

```
1. User posts on Nostr
   ↓
2. Terminal-HQ subscribes to relays, sees new post
   ↓
3. Extract author's npub from event
   ↓
4. Check credit balance: GET /api/v1/user/{npub}
   ↓
5. If balance >= 1 sat:
   - Send message to satellite via HSModem
   - Deduct credit: POST /api/v1/user/{npub}/deduct
   ↓
6. Satellite broadcasts globally
   ↓
7. Off-grid users receive via satellite RX
```

### Inbound Flow (Satellite → Internet)

```
1. Off-grid user transmits via satellite
   ↓
2. Terminal-HQ satellite modem receives signal
   ↓
3. HSModem + Oscar software decode message
   ↓
4. Oscar writes .txt file with decoded data
   ↓
5. Terminal-HQ monitor script detects new file
   ↓
6. Parse message (npub, content, tags)
   ↓
7. Bot signs Nostr event with its key
   ↓
8. Publish to multiple Nostr relays
   ↓
9. Internet users see the post
```

### Credit Management Flow

```
1. User sends DM to bot: /topup 1000
   ↓
2. Bot calls: POST /api/v1/user/{npub}/invoice?amount=1000
   ↓
3. LNbits generates Lightning invoice (bolt11)
   ↓
4. Bot sends invoice to user via encrypted DM
   ↓
5. User pays invoice with Lightning wallet
   ↓
6. LNbits detects payment via webhook
   ↓
7. BitSatCredit extension credits user balance
   ↓
8. User can now send 1000 messages (1 sat each)
```

---

## Message Format

When Terminal-HQ relays a message via satellite, it formats it for off-grid readability:

### Regular Post
```
🛰️Off-Grid Relayed via satellite🛰️
--------------------------------

nostr:npub1user... said:
This is my message content that was sent via satellite!

--------------------------------
📡 BitSatRelay - Terminal-HQ
```

### Reply
```
🛰️Off-Grid Relayed via satellite🛰️
--------------------------------

↩️ REPLY to nostr:npub1someone...
Re: nostr:note1abc123... (event reference)

nostr:npub1user... said:
This is my reply message

--------------------------------
📡 BitSatRelay - Terminal-HQ
```

### Quote/Repost
```
🛰️Off-Grid Relayed via satellite🛰️
--------------------------------

💬 QUOTE to nostr:npub1original...

nostr:npub1user... said:
My commentary on the quoted post

[Original quoted message appears here]

--------------------------------
📡 BitSatRelay - Terminal-HQ
```

This format ensures off-grid users can understand context even without access to the full Nostr network.

---

## Pricing & Economics

**Cost Structure:**
- **1 sat per message** (configurable)
- Minimum top-up: 10 sats
- No subscription fees
- Pay only for what you send

**Why pay-per-message?**
- Prevents spam
- Funds satellite bandwidth costs
- Fair usage model
- Aligns incentives (users value their messages)

**Revenue Model:**
- Users pay sats to send
- Funds cover satellite service costs (~$50-200/month)
- Terminal-HQ operator covers infrastructure
- Goal: Break-even or slight profit for sustainability

---

## Security & Privacy

### Message Security
- All Nostr events cryptographically signed (NIP-01)
- DMs encrypted end-to-end (NIP-04 with AES-256-CBC)
- Bot identity verifiable via npub
- No message content stored permanently

### Credit Security
- Server-side validation prevents local tampering
- Lightning invoices are trustless
- API endpoints rate-limited
- No plaintext private keys in configs

### Spam Prevention
- Rate limiting: 5 second minimum between messages
- Credit requirement: must pay to send
- DM bot rate limits: 5 seconds per user
- Duplicate message detection

---

## Technical Specifications

### Nostr Protocol Support
- **NIP-01**: Basic protocol (event structure, signatures)
- **NIP-04**: Encrypted Direct Messages
- **NIP-10**: Text notes and reply threading
- **NIP-18**: Reposts and quote reposts
- **NIP-19**: Bech32-encoded identifiers (npub, note)

### Satellite Protocol
- **Amateur Geostationary Relay Satellite**
- **Uplink**: 2.4 GHz (13cm band)
- **Downlink**: 10.489 GHz (Ku band)
- Custom HSModem protocol
- Packet-based transmission
- Multi-frame support for large messages
- Automatic retry on failure

### API Endpoints (BitSatCredit)

**Get User Balance**
```
GET /api/v1/user/{npub}

Response:
{
  "npub": "npub1...",
  "balance_sats": 500,
  "total_deposited": 1000,
  "total_spent": 500,
  "message_count": 500
}
```

**Generate Invoice**
```
POST /api/v1/user/{npub}/invoice?amount=1000

Response:
{
  "topup_id": "abc123",
  "payment_hash": "def456",
  "bolt11": "lnbc10000n..."
}
```

**Deduct Credit**
```
POST /api/v1/user/{npub}/deduct
Body: {"amount": 1, "memo": "SAT TX"}

Response:
{
  "success": true,
  "new_balance": 499
}
```

---

## Deployment Requirements

### Terminal-HQ Minimum Specs
- **OS**: Ubuntu 20.04+ or Debian-based Linux
- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum
- **Storage**: 20GB+ SSD
- **Network**: Stable internet (fiber/cellular)
- **Python**: 3.8+

### Required Hardware WIP
- **Satellite modem**: HSModem or compatible
- **Uplink**: 2.4 GHz transmitter (13cm amateur band)
- **Downlink**: 10.489 GHz receiver (Ku band)
- Satellite dish with appropriate feed for both bands
- Network connection to modem (TCP/IP)

### Software Dependencies
```bash
# Python packages
nostr
requests
asyncio
websocket-client
cryptography

# System packages
python3-pip
git
```

### LNbits Setup
- LNbits v0.12+ (self-hosted or cloud)
- Lightning funding source configured
- BitSatCredit extension installed

---

## Configuration

### Main Config (relay_config.json)
```json
{
  "bitsatcredit_extension": {
    "url": "https://your-lnbits.com/bitsatcredit"
  },
  "nostr": {
    "bot_nsec": "nsec1...",
    "bot_npub": "npub1...",
    "relay_urls": [
      "wss://relay.damus.io",
      "wss://nos.lol",
      "wss://relay.nostr.band"
    ]
  },
  "hsmodem": {
    "host": "192.168.1.112",
    "port": 40132
  },
  "pricing": {
    "price_per_message_sats": 1
  },
  "dm_notifications": {
    "enabled": true,
    "low_balance_threshold_sats": 100,
    "critical_balance_threshold_sats": 10
  }
}
```

---

## Use Cases

### 1. Emergency Communications
When internet goes down due to natural disaster, users can still communicate via satellite using Terminal-1 units.

### 2. Censorship Resistance
Governments can't block satellite signals. If a country censors Nostr, users relay messages via satellite to reach the outside world.

### 3. Remote/Off-Grid Operations
Maritime, aviation, remote research stations, or rural areas without internet can stay connected to Nostr.

### 4. Disaster Recovery
During hurricanes, earthquakes, or infrastructure failures, BitSatRelay maintains communication when cellular and internet are down.

### 5. Freedom of Speech
Journalists, activists, and citizens in oppressive regimes can communicate freely without fear of ISP monitoring or blocking.

---

## Future Development

### Phase 1: Geographic Redundancy (In Progress)
- Deploy Terminal-HQ2 in different continent
- Shared bot identity and credit pool
- Automatic failover if one HQ goes offline
- Goal: 99.9% uptime

### Phase 2: User Terminals (Planned)
- Terminal-1: Off-grid user kit
- Raspberry Pi 4 + HSModem + solar power
- Local Nostr relay (strfry)
- WiFi access point for user devices
- Full TX+RX capability

### Phase 3: LoRa Mesh Integration (Future)
- Local relay via LoRa mesh
- Terminal-1 units form local networks
- Share satellite uplink among nearby users
- Extend range without additional satellites

### Phase 4: Global Network (Vision)
- Terminal-HQ in every continent
- Thousands of Terminal-1 units deployed
- Mesh networks in major cities
- Truly global, unstoppable communications

---

## System Components Detail

### BitSatRelay.py (Main Orchestrator)

Runs three parallel async tasks:

**1. Outbound Bridge**
- Subscribes to configured Nostr relays
- Filters for new events (kind 1: text notes)
- Extracts author npub from event
- Checks credit balance via API
- Deducts credit and sends to satellite
- Rate limits per user (5 second minimum)

**2. Inbound Monitor**
- Watches Oscar data directory for new .txt files
- Parses satellite messages
- Reconstructs Nostr events
- Signs with bot's nsec
- Publishes to all configured relays
- Archives processed files

**3. DM Bot**
- Monitors for kind 4 events (encrypted DMs)
- Decrypts using NIP-04 (shared secret ECDH)
- Parses commands (/balance, /topup, /help)
- Calls LNbits API for balance/invoice
- Encrypts responses and sends via DM
- Sends low balance warnings automatically

### BitSatCredit Extension

**Components:**
- `views_api.py`: REST API endpoints
- `crud.py`: Database operations
- `services.py`: Business logic
- `tasks.py`: Payment webhook handler
- `models.py`: Data structures

**Database Schema:**
- Users: npub, balance, totals, message count
- Transactions: deposits and spends with history
- TopUp Requests: pending and paid invoices

**Payment Flow:**
1. User requests invoice
2. Extension creates invoice via LNbits core
3. Stores topup request in database
4. Returns bolt11 to user
5. Webhook detects payment
6. Credits user balance automatically
7. Creates transaction record

---

## Performance Metrics

### Current System (Single Terminal-HQ)
- **Throughput**: ~10-20 messages/minute
- **Latency**: 30-60 seconds (Nostr → Satellite)
- **Uptime**: 95%+ (limited by single HQ)
- **Coverage**: Global (single satellite)

### Target (Multi-HQ Network)
- **Throughput**: 100+ messages/minute
- **Latency**: <30 seconds
- **Uptime**: 99.9% (geographic redundancy)
- **Coverage**: Global 24/7

---

## Community & Support

### Open Source
- **Code**: Available on GitHub
- **License**: MIT License
- **Contributions**: Welcome via pull requests

### Getting Started
1. Read this [README](README.md)
2. Review [System Architecture](docs/ARCHITECTURE.md)
3. Check hardware requirements
4. Follow the [Setup Guide](docs/SETUP.md)
5. Deploy Terminal-HQ
6. Join Nostr for community support

### Contact
- **Nostr**: `npub18cel6ufy7960c5632xfhlpccvdxankzkzs75ema45yxa4uhkzhqqsrulqe`
- **GitHub**: https://github.com/CryptoIceMLH
- **Website**: https://www.molonlabe.holdings/

---



-

---

## License

MIT License - see [LICENSE](LICENSE) file for details

---

## Version History

- **BitSatRelay v1.0-WIP**: Initial public release (Work in Progress)
  - Core codebase and architecture
  - Redacted sensitive info
  - Initial documentation (setup guides in progress)
  - HSModem, strfry relay, and networking docs coming soon
  - Community contributions welcome

- **v7**: Production deployment (current)
  - Three-system architecture
  - DM bot with invoice generation
  - BitSatCredit v1.6.1
  - Stable operations

- **v6**: Credit system integration
  - LNbits integration
  - Pay-per-message model
  - Balance tracking

- **v5**: Bidirectional communications
  - Satellite TX + RX
  - Inbound message processing

- **v4 and earlier**: Development iterations

---

**BitSatRelay: Communications that can't be stopped.**

🛰️ **Freedom. Privacy. Resilience.** ⚡
