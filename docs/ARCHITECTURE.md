# BitSatRelay System Architecture v2.0
**Decentralized Bitcoin-Nostr Satellite Communications**

**Date**: 2025-12-02
**Status**: Production (Terminal-HQ) + Planned Expansion (HQ2, Terminal-1)

---

## Executive Summary

BitSatRelay is a satellite-based Nostr communications system that works with or without internet connectivity. The system bridges internet-connected Nostr relays with off-grid satellite communications, enabling censorship-resistant messaging during disasters, internet outages, or in remote locations.

**Current State**: Single Terminal-HQ operational with 3-system architecture (outbound bridge, inbound monitor, DM bot)
**Next Phase**: Add redundant HQ2 + build user Terminal-1 kits
**Future**: LoRa mesh integration for local relay networks

---

## System Components

### 1. Terminal-HQ (Production - Operating Now)

**Hardware**:
- **Computer**: Ubuntu Linux server @ 192.168.1.111
- **Satellite Modem**: HSModem @ 192.168.1.112:40132 (custom-built TX/RX hardware)
- **Satellite System**: Your proprietary satellite uplink/downlink
- **Internet**: Fiber/cellular (for Nostr relay connections + LNbits API)
- **Network**: 192.168.1.x local LAN
- **Storage**: SMB share @ 192.168.1.112 (`/run/user/1000/gvfs/smb-share:server=192.168.1.112,share=oscardata/RXimages/`)

**Software Stack**:
```
BitSatRelay.py (V7sensetive) - Main orchestrator running 3 parallel async tasks:
├── Outbound Bridge: Nostr events → HSModem → Satellite TX
├── Inbound Monitor: Oscar .txt files → Parse → Nostr relay publish
└── DM Bot: NIP-04 encrypted DMs for credit management
```

**Key Services**:
- **LNbits**: https://lnbits.molonlabe.holdings (Umbrel-hosted)
  - BitSatCredit extension v1.6.1
  - Wallet: `6e1faaf6356b43029124fdeb5f93a297`
  - API endpoints: `/api/v1/user/{npub}`, `/api/v1/user/{npub}/invoice`, `/api/v1/user/{npub}/deduct`

- **Nostr Bot**:
  - npub: `npub14uee3fwxjwq7m25gsyqguv2t6v8ft69jax4lvs3skfpa8u7thdsqpu7gam`
  - nsec: [REDACTED - stored in relay_config.json]
  - Connects to 9 public relays (damus, knostr, bitsat.molonlabe, nos.lol, etc.)
  - Local monitor relay: ws://localhost:7777

- **Pricing**: 1 sat per satellite message
- **Rate Limiting**: 5 second minimum between messages per user
- **DM Commands**: `/balance`, `/topup <amount>`, `/help`

**Data Flow (Normal Operation)**:
```
Internet Nostr Post → HQ subscribes → Check credit → HSModem TX → Satellite
                                                                      ↓
Satellite → HSModem RX → Oscar writes .txt → HQ parses → Post to Nostr
```

---

### 2. Terminal-HQ2 (Planned - Global Decentralization)

**Purpose**: Geographically distributed HQ terminals to maintain global communications when regional ISPs fail or are censored

**Hardware**: Clone of Terminal-HQ
- Ubuntu Linux server (different IP)
- HSModem satellite modem (separate physical unit)
- Same satellite hardware specs
- Internet connection (different ISP/region)
- **CRITICAL**: Geographic separation in different countries/continents to survive regional internet blackouts, ISP censorship, or infrastructure attacks

**Software**: Exact copy of V7sensetive
- Same BitSatRelay.py scripts
- Same relay_config.json structure
- **DECISION**: Use SAME bot npub/nsec (shared identity - users see one bot)
- **DECISION**: Use SAME LNbits wallet `6e1faaf6356b43029124fdeb5f93a297` (shared credit pool)

**Why Shared Identity**:
- Users don't care which HQ they're talking to
- Single DM conversation thread
- Single credit balance
- Simpler UX
- Seamless global operations - if one region goes dark, another keeps the network alive

**Global Communication Scenarios**:

**Scenario 1: Regional ISP Blackout (e.g., Europe Down)**
```
Europe ISP: DOWN ❌
HQ1 (Europe): Offline
         ↓
Nostr → HQ2 (Asia/US) → Satellite → Global coverage maintained
         ↓
European users still receive via satellite
Europeans can TX via Terminal-1 to HQ2
```

**Scenario 2: All HQs Online (Normal Global Operations)**
```
Nostr → HQ1 (Europe) → Satellite (covers Europe/Africa)
     → HQ2 (Asia) → Satellite (covers Asia/Pacific)
     → HQ3 (Americas) → Satellite (covers North/South America)
         ↓
    Global 24/7 coverage across all time zones
```

**Scenario 3: Censorship Attack (Government Blocks HQ1)**
```
Government blocks HQ1 ISP
         ↓
Nostr → HQ2/HQ3 → Satellite (route around censorship)
         ↓
HQ1: Satellite RX still works, queues outbound
Uses VPN/Tor when possible to sync
```

**Scenario 4: Nuclear/EMP Attack (Multiple Regions Offline)**
```
Terminal-1 users → Satellite → HQ1/HQ2 (RX only)
                                   ↓
                        Local storage, no Nostr publish
                        Emergency mode: skip credit checks
                        When online: bulk sync + reconcile credits
```

---

### 3. Terminal-1 (User Terminal - To Be Built)

**Purpose**: Off-grid personal Nostr terminal for satellite comms

**Build Spec** (TX+RX Full Version):
- **SBC**: Raspberry Pi 4 (4GB RAM) - $55
- **OS**: Raspberry Pi OS Lite (Debian-based, headless)
- **Storage**: 128GB USB SSD - $25
- **Modem**: HSModem (TX+RX capable)
- **Power**: 50W solar panel + 25,000mAh battery + charge controller - $100
- **Case**: Weatherproof enclosure - $30
- **Total**: ~$210 + modem

**Software Stack**:
```
Raspberry Pi 4
├── Raspberry Pi OS Lite (no GUI)
├── strfry (local Nostr relay) - C++, 100MB RAM
├── hostapd (WiFi Access Point: "BitSatRelay-T1")
├── satellite_monitor.py (RX: Oscar → strfry)
├── terminal1_bridge.py (TX: strfry → HSModem)
└── credit_sync.py (sync to LNbits when internet available)
```

**Why strfry**:
- C++ native (fast, low memory)
- Battle-tested (used by major public relays)
- 100-200MB RAM usage (fits Pi 4)
- Simple config
- SQLite database

**User Experience**:
1. Terminal-1 boots, starts WiFi AP "BitSatRelay-T1"
2. User connects phone to WiFi
3. User opens Damus/Amethyst/any Nostr app
4. Add relay: `ws://192.168.4.1:7777`
5. Post as normal - Terminal-1 handles satellite sync

**No special apps needed - any Nostr client works!**

**Portal Architecture**:
```
┌──────────────┐
│ User's Phone │ (Any Nostr app)
└──────┬───────┘
       │ WiFi
       ↓
┌─────────────────────────────┐
│      Terminal-1 (Pi 4)       │
│                              │
│  ┌────────────────────────┐ │
│  │ strfry Local Relay     │ │ ← Stores events locally
│  │ ws://192.168.4.1:7777  │ │
│  └────────────────────────┘ │
│            ↕                 │
│  ┌────────────────────────┐ │
│  │ satellite_monitor.py   │ │ ← RX: Satellite → strfry
│  │ terminal1_bridge.py    │ │ ← TX: strfry → Satellite
│  └────────────────────────┘ │
│            ↕                 │
│  ┌────────────────────────┐ │
│  │ HSModem (192.168.4.1)  │ │
│  └────────────────────────┘ │
└──────────────┬───────────────┘
               │
               ↓
         Satellite
               ↓
         Terminal-HQ
               ↓
          Internet Nostr
```

**Credit System (Terminal-1)**:

**Online Mode** (has internet via phone tethering):
```python
# Real-time credit check
balance = requests.get(f"{LNBITS_URL}/api/v1/user/{npub}")
if balance < 1:
    reject_message()
else:
    send_to_satellite()
    requests.post(f"{LNBITS_URL}/api/v1/user/{npub}/deduct", json={"amount": 1})
```

**Offline Mode** (no internet):
```python
# Use cached balance
balance_cache = load_local_cache()  # Last known balance
if balance_cache['balance'] > balance_cache['pending_charges']:
    send_to_satellite()
    balance_cache['pending_charges'] += 1
    save_cache()
else:
    queue_message()  # Try again when credits available
```

**Sync When Online**:
```python
# USB tethering detected internet
pending = load_pending_charges()
for charge in pending:
    lnbits.deduct_credit(npub, 1)

new_balance = lnbits.get_balance(npub)
update_cache(new_balance)
clear_pending()
```

**Emergency Mode** (all HQs offline):
```python
# Disaster scenario - allow limited free messages
if messages_today < 50:  # Rate limit
    send_to_satellite()
    log_for_later_billing()
else:
    reject_with_message("Emergency quota exceeded")
```

---

## Credit System Architecture

### Current State (Production)

**Single Wallet Model**:
- LNbits wallet: `6e1faaf6356b43029124fdeb5f93a297`
- All users share this wallet for payments
- HQ1 deducts 1 sat per message
- DM bot generates invoices via `/api/v1/user/{npub}/invoice`

**Flow**:
```
User sends DM: /topup 1000
    ↓
Bot calls: POST /api/v1/user/{npub}/invoice?amount=1000
    ↓
LNbits generates Lightning invoice
    ↓
Bot sends invoice to user via DM
    ↓
User pays invoice
    ↓
LNbits webhook detects payment
    ↓
BitSatCredit extension credits user balance
    ↓
User can send 1000 messages (1 sat each)
```

### Multi-HQ Expansion (HQ2)

**DECISION**: Shared wallet across HQ1 and HQ2

**Why**:
- Simpler for users (one balance)
- Automatic failover (any HQ can deduct)
- No credit fragmentation
- Operators share bandwidth costs

**How**:
- HQ1 and HQ2 both call same LNbits API
- Race condition handled by LNbits (atomic balance updates)
- If user sends via HQ1 and HQ2 simultaneously: both deduct, first one wins
- Rare edge case, acceptable loss

**API Calls**:
```python
# Both HQs use same code
balance = requests.get("https://lnbits.molonlabe.holdings/api/v1/user/{npub}")
if balance >= 1:
    send_satellite()
    requests.post("https://lnbits.molonlabe.holdings/api/v1/user/{npub}/deduct",
                  json={"amount": 1, "memo": f"SAT TX via {HQ_ID}"})
```

### Offline Reconciliation

**Problem**: HQ loses internet mid-operation

**Solution**: Local queue + post-sync

```python
# HQ offline detection
try:
    balance = api.get_balance(npub)
except ConnectionError:
    # Offline mode
    balance = cache.get_balance(npub)
    if balance > 0:
        send_satellite()
        pending_queue.append({"npub": npub, "amount": 1, "timestamp": now()})
        cache.deduct_local(npub, 1)
    else:
        reject("Insufficient cached balance")

# When internet returns
def sync_pending():
    for charge in pending_queue:
        try:
            api.deduct(charge['npub'], charge['amount'])
        except InsufficientBalance:
            # User spent credits elsewhere, bill them retroactively
            api.create_debt(charge['npub'], charge['amount'])
    clear_queue()
```

---

## Data Flow Diagrams

### Flow 1: User Posts from Internet → Satellite

```
[User Nostr Client]
    ↓ posts event
[Public Nostr Relays] (relay.damus.io, nos.lol, etc.)
    ↓ websocket subscription
[Terminal-HQ BitSatRelay.py - Outbound Bridge]
    ↓ checks event
GET /api/v1/user/{author_npub}  → [LNbits API]
    ↓ if balance >= 1
POST /api/v1/user/{author_npub}/deduct {"amount": 1}
    ↓
[HSModem.send_packet()]
    ↓
[Satellite TX]
    ↓ broadcast
[All listening terminals receive]
```

### Flow 2: Off-Grid User Sends via Terminal-1

```
[User's Phone Nostr App]
    ↓ ws://192.168.4.1:7777
[Terminal-1 strfry relay]
    ↓ event stored
[terminal1_bridge.py monitors strfry]
    ↓ new event detected
Check cached balance (or API if online)
    ↓ if ok
[HSModem TX]
    ↓
[Satellite]
    ↓
[Terminal-HQ receives]
    ↓ validates credit server-side
[HQ posts to internet Nostr]
```

### Flow 3: Satellite → Internet (Inbound)

```
[Satellite RX]
    ↓
[HSModem writes data]
    ↓
[Oscar software processes]
    ↓ writes .txt file
[SMB Share: /RXimages/filename.txt]
    ↓ file watcher
[Terminal-HQ satellite_monitor.py]
    ↓ parses .txt
[Extract: npub, content, tags]
    ↓ create Nostr event
[Bot signs event with nsec]
    ↓
[Publish to 9 Nostr relays]
    ↓
[Internet users see post]
```

### Flow 4: HQ1 Fails, HQ2 Takes Over

```
[Nostr User Posts]
    ↓
HQ1: OFFLINE ❌
HQ2: ONLINE ✅ → processes event → Satellite
    ↓
[All users continue normally]

Meanwhile:
HQ1: Satellite RX still works → queues outbound → waits for internet
When HQ1 returns: syncs queue to Nostr
```

---

## Implementation Roadmap

### Phase 1: Terminal-HQ2 Redundancy (4 weeks)

**Week 1-2: Hardware Setup**
- [ ] Acquire second Ubuntu server
- [ ] Clone HSModem hardware
- [ ] Set up satellite dish (separate location if possible)
- [ ] Configure network (different IP range or VPN)

**Week 3: Software Deployment**
- [ ] Clone V7sensetive folder to HQ2
- [ ] Update relay_config.json:
  - New HSModem IP
  - New Oscar data path
  - SAME bot nsec/npub
  - SAME LNbits URL + wallet
- [ ] Test satellite TX/RX independently
- [ ] Test LNbits API access

**Week 4: Testing & Cutover**
- [ ] Run HQ1 and HQ2 in parallel for 7 days
- [ ] Monitor for credit conflicts
- [ ] Test failover: kill HQ1, verify HQ2 continues
- [ ] Test load balancing: both online
- [ ] Document procedures

**Success Criteria**:
- Both HQs process messages without errors
- Credit deductions don't double-charge
- Failover takes <60 seconds

---

### Phase 2: Terminal-1 Prototype (6 weeks)

**Week 1: Hardware Acquisition**
- [ ] Order Pi 4 (4GB) + SSD + solar kit
- [ ] Order HSModem (TX+RX capable)
- [ ] 3D print or buy weatherproof case

**Week 2-3: Software Development**
- [ ] Install Raspberry Pi OS Lite
- [ ] Compile and install strfry
- [ ] Configure hostapd WiFi AP
- [ ] Port satellite_monitor.py from V7sensetive
- [ ] Write terminal1_bridge.py (new component)
- [ ] Write credit_sync.py (new component)

**Week 4: Integration Testing**
- [ ] Test RX: Satellite → strfry
- [ ] Test WiFi: Phone → strfry
- [ ] Test TX: strfry → Satellite
- [ ] Test credit caching offline
- [ ] Test credit sync when online

**Week 5: Field Testing**
- [ ] Deploy Terminal-1 at test location (off-grid)
- [ ] User test with Damus app
- [ ] Monitor power consumption (verify solar sufficient)
- [ ] Test 48-hour continuous operation
- [ ] Collect bugs and issues

**Week 6: Image Creation**
- [ ] Create reproducible SD card image
- [ ] Write setup documentation
- [ ] Create config wizard script
- [ ] Test fresh install on blank Pi
- [ ] Publish image to GitHub releases

**Deliverables**:
- Working Terminal-1 prototype
- Pre-built SD card image (~4GB)
- User manual (markdown)
- Hardware BOM (bill of materials)

---

### Phase 3: Emergency Mode & Offline Logic (2 weeks)

**Week 1: Offline Credit Logic**
- [ ] Implement local cache in terminal1_bridge.py
- [ ] Add pending charge queue
- [ ] Add credit_sync service
- [ ] Test offline→online transition

**Week 2: Emergency Bypass**
- [ ] Add HQ offline detection
- [ ] Implement 50 msg/day emergency quota
- [ ] Add post-billing reconciliation
- [ ] Test total blackout scenario

---

### Phase 4: Production Deployment (Ongoing)

**Terminal-1 User Distribution**:
- [ ] Build 10 initial user kits
- [ ] Distribute to beta testers
- [ ] Collect feedback
- [ ] Iterate on design
- [ ] Scale production

**Revenue Model**:
- Users pay 1 sat per message
- Need ~40,000 messages/month to break even on HQ costs
- Consider:
  - Increasing price to 2-5 sats
  - Donation model
  - Freemium (free RX, paid TX)

---

## Security Model

### Credit Fraud Prevention

**Attack**: User modifies local cache to fake high balance

**Mitigation**:
- HQ validates ALL credits server-side
- Local cache is optimization only
- If server says no credit → message rejected
- User can't bypass HQ validation

### Satellite Spam Prevention

**Attack**: User floods satellite with spam

**Mitigation**:
- Rate limiting: 5 second minimum between messages
- Credit cost: spamming costs money
- HQ can blacklist abusive npubs
- Emergency mode has 50 msg/day hard cap

### Bot Impersonation

**Attack**: Fake HQ posts malicious content

**Mitigation**:
- All HQ posts signed with bot nsec
- Users verify NIP-01 signatures
- Official bot npub published
- DNS: bitsat.molonlabe.holdings points to real relay

### Offline Credit Theft

**Attack**: User exploits offline mode for free messages

**Mitigation**:
- Emergency mode rate limited to 50 msg/day
- Post-billing when online
- Negative balance tracking
- Account suspension if balance < -100 sats

---

## Cost Analysis

### Terminal-HQ (Current Monthly Cost)
- Hardware amortized: ~$100/mo
- Satellite service: $50-200/mo (depends on provider)
- Internet: $50/mo
- Power: $10/mo
- **Total**: ~$210-360/mo

### Terminal-HQ2 (Additional Monthly Cost)
- Same as HQ1: ~$210-360/mo
- **Total both HQs**: ~$420-720/mo

### Revenue (Current Usage)
- Average: 1000 messages/day
- @ 1 sat/msg = 1000 sats/day
- @ $0.0005/sat = $0.50/day = $15/mo
- **NOT PROFITABLE**

### Break-Even Analysis
- Need: $420/mo revenue minimum
- @ 1 sat/msg = 840,000 messages/mo
- = 28,000 messages/day
- = 1.17 messages/minute (24/7)

**Options**:
1. Increase price: 5 sats/msg → need 168,000 msg/mo
2. Freemium: Free RX, 10 sats for TX
3. Donation model: Community funded
4. Sponsorship: Companies pay for access

---

## Success Metrics

### Technical KPIs
- **Uptime**: >99% (combined HQ1+HQ2)
- **Latency**: <60s (Nostr post → satellite received)
- **Message Loss**: <1%
- **Failover Time**: <60s (HQ1 dies → HQ2 takes over)

### User Growth
- **Active Terminals**: Track Terminal-1 deployments
- **Daily Messages**: Messages/day via satellite
- **Credit Loaded**: Total sats deposited

### Financial
- **Revenue**: Total sats collected/mo
- **Burn Rate**: Monthly operational costs
- **Runway**: Months until break-even

---

## Open Questions (DECISIONS NEEDED)

### 1. Terminal-1 Default Configuration
**Question**: Ship RX-only or TX+RX by default?

**Proposal**: Ship TX+RX kit, user can disable TX if desired

**Rationale**:
- Most users want bidirectional
- Cheaper to build one kit than two SKUs
- Power consumption difference minimal

**DECISION**: ___________________

---

### 2. Emergency Mode Limits
**Question**: How many free messages during internet blackout?

**Proposal**: 50 messages per user per day

**Rationale**:
- Enough for emergency comms
- Not enough for spam
- ~$0.025 cost risk per user per day

**DECISION**: ___________________

---

### 3. LoRa Mesh Integration Timeline
**Question**: When to start LoRa development?

**Proposal**: After 50+ Terminal-1 units deployed

**Rationale**:
- Need user base first
- Mesh only useful with density
- Focus on satellite first

**DECISION**: ___________________

---

## Appendix A: File Structure

```
E:\MLH BTC\btcsatcoms\
├── Relay radio scripts\
│   ├── V7sensetive\              ← Current production (Terminal-HQ)
│   │   ├── BitSatRelay.py        ← Main orchestrator
│   │   ├── nostr_bot.py          ← Nostr event handling
│   │   ├── dm_bot.py             ← DM credit management
│   │   ├── bitsatcredit_client.py ← LNbits API client
│   │   ├── satellite_monitor.py  ← Inbound Oscar parser
│   │   └── relay_config.json     ← Configuration
│   │
│   └── V8_Terminal1\             ← Future: Terminal-1 build
│       ├── terminal1_main.py
│       ├── satellite_monitor.py  (adapted from V7)
│       ├── terminal1_bridge.py   (new)
│       ├── credit_sync.py        (new)
│       └── terminal1_config.json
│
├── LNbitextension\
│   └── bitsatcredit\             ← LNbits extension v1.6.1
│       ├── views_api.py          ← API endpoints
│       ├── crud.py               ← Database operations
│       ├── services.py           ← Business logic
│       └── tasks.py              ← Payment webhooks
│
└── Architecture\
    └── BitSatRelay-System-Architecture-v2.md ← THIS FILE
```

---

## Appendix B: Terminal-1 Config Example

```json
{
  "terminal_type": "user",
  "terminal_id": "terminal1_alpha",
  "hardware": {
    "hsmodem_host": "192.168.4.1",
    "hsmodem_port": 40132
  },
  "wifi_ap": {
    "enabled": true,
    "ssid": "BitSatRelay-T1",
    "password": "satcomms2024",
    "ip": "192.168.4.1",
    "dhcp_range": "192.168.4.100-192.168.4.200"
  },
  "local_relay": {
    "type": "strfry",
    "bind": "0.0.0.0",
    "port": 7777,
    "database": "/var/lib/bitsatrelay/strfry.db"
  },
  "satellite": {
    "rx_enabled": true,
    "tx_enabled": true,
    "rx_data_path": "/var/lib/bitsatrelay/rxdata/"
  },
  "credit": {
    "api_url": "https://lnbits.molonlabe.holdings/bitsatcredit",
    "cache_file": "/var/lib/bitsatrelay/credit_cache.json",
    "sync_interval_seconds": 300,
    "price_per_message": 1
  },
  "user": {
    "npub": "npub1...",
    "emergency_mode": {
      "enabled": true,
      "max_messages_per_day": 50
    }
  }
}
```

---

**END OF DOCUMENT**

**Next Actions**:
1. Review with team
2. Make decisions on open questions
3. Begin Phase 1: HQ2 hardware acquisition
4. Update this doc as system evolves
