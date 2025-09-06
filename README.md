# Nostr-QO100 Satellite Bridge Project

This R&D project uses QO-100 amateur satellite as a development testbed to validate Bitcoin and Nostr satellite bridge concepts. The goal is to create complementary infrastructure to Blockstream's satellite services, providing network diversity and resilience for the Bitcoin ecosystem.

## Project Mission

Building a satellite communication bridge that supports **Bitcoin** and **Nostr** protocols, designed as a complementary service to **Blockstream's satellite node infrastructure**. This creates redundant, censorship-resistant communication channels for the Bitcoin ecosystem via multiple satellite providers and protocols.

UPDATE: with first working release 5/9/2025


## Overview

I'm building a bridge system that connects **Nostr** (a decentralized social protocol) with satellite communications for off-grid messaging. Currently using the **QO-100 amateur radio satellite** as a proof-of-concept testbed to validate the technical approach and demonstrate feasibility.

**Current Development Strategy**: QO-100 serves as our R&D platform due to its free access and established amateur radio community. Once the concept proves viable and funding is secured, the goal is to scale to **commercial satellite providers** with dedicated bandwidth, creating an alternative and complement to existing Bitcoin satellite services like Blockstream's infrastructure.

## Project Goals

### **Phase 1: Proof of Concept** *(Using QO-100 Amateur Satellite)*
- **Technical Validation**: Prove Nostr ↔ satellite bridge concept works
- **Protocol Development**: Establish reliable message routing for Bitcoin/Nostr data
- **Community Testing**: Leverage amateur radio community for feedback and iteration
- **Cost-Free R&D**: Utilize free amateur satellite access for development
- **Blockstream Complement**: Develop alternative to/backup for Blockstream satellite service

### **Phase 2: Commercial Deployment** *(Target: Commercial Satellites)*
- **Dedicated Bandwidth**: Rent transponder time from commercial satellite operators
- **Bitcoin Infrastructure**: Support Bitcoin node sync, Lightning Network, and Nostr relays
- **Global Coverage**: Multiple satellites for worldwide 24/7 Bitcoin/Nostr access
- **Service Diversity**: Provide alternative to single-provider satellite solutions

## Current Status ✅

### **Phase 1: Core Bridge Development** *(COMPLETED)*

**What I've Built:**
- Full Nostr relay integration with real-time WebSocket monitoring
- HSModem external interface communication (Type 3 ASCII protocol)
- Robust error handling and automatic reconnection
- Message formatting with callsign/timestamp headers
- Connection testing and validation

**Technical Implementation:**
- Python asyncio for concurrent relay monitoring
- UDP packet construction for HSModem external interface
- Message length limiting and encoding safety
- Configurable relay and HSModem endpoints

### **Phase 2: Protocol Integration** *(IN PROGRESS)*

**Currently Working On:**
- Fine-tuning HSModem packet structure and timing
- Testing message delivery reliability
- Optimizing for QO-100's narrowband constraints
- Implementing bidirectional communication

**Next Steps:**
- Multi-packet message support for longer content
- Message acknowledgment system
- QSO logging integration
- Web interface for monitoring

## Technical Architecture

**Current Development Setup (QO-100):**
```
[Nostr Clients] → [Nostr Relay] → [Bridge Script] → [HSModem] → [QO-100 Amateur Satellite] → [Ham Stations]
```

**Future Commercial Architecture (Bitcoin/Nostr Satellite Network):**
```
[Bitcoin Nodes] → [Nostr Relays] → [Bridge Infrastructure] → [Commercial Satellites] → [Global Bitcoin/Nostr Users]
                                                           ↓
                                        [Complement to Blockstream Satellite]
```

### Key Components

1. **Nostr Integration**
   - WebSocket connection to local/remote relay
   - Real-time event monitoring (kind 1 messages)  
   - JSON-RPC subscription handling

2. **HSModem Interface**
   - External UDP interface on port 40135
   - Type 3 (ASCII File) message format
   - 224-byte packet structure with proper headers

3. **Message Processing**
   - Content filtering and length limiting
   - Timestamp and author formatting
   - ASCII encoding with error handling

## Configuration

- **Relay**: `ws://localhost:7777` (local relay instance)
- **HSModem**: `192.168.1.112:40135` (Windows machine)
- **Message Type**: Type 3 (ASCII File)
- **Max Message**: 200 characters (narrowband optimized)

## Testing & Validation

- ✅ HSModem connection testing
- ✅ Packet structure validation  
- ✅ Message encoding/formatting
- 🔄 End-to-end satellite transmission
- 🔄 Multi-station reception testing

## Future Roadmap

### **Phase 3: Commercial Transition**
- Market validation and user acquisition
- Funding round for satellite bandwidth rental
- Partnership negotiations with satellite operators (Inmarsat, Iridium, etc.)
- Professional modem hardware integration

### **Phase 4: Enhanced Features**
- Bidirectional message routing (satellite → Nostr)
- Message threading and conversation tracking  
- Multiple relay support and failover
- Encrypted message support

### **Phase 5: User Interface**
- Web dashboard for monitoring
- Mobile app integration
- QSO logging and statistics
- Network topology visualization

### **Phase 6: Network Effects**
- Multiple bridge nodes
- Mesh network capabilities
- Emergency communication protocols
- Integration with existing ham radio tools

## Why This Matters

This project bridges decentralized internet protocols (Nostr) with satellite communications, creating new possibilities for truly global, censorship-resistant messaging.

**Current Development with QO-100 Amateur Satellite:**
- **Free R&D Platform**: Amateur satellite provides cost-free testing environment
- **Proven Technology**: QO-100 has established user base and reliable uptime
- **Community Validation**: Ham radio operators provide expert technical feedback
- **Protocol Foundation**: Develops core Bitcoin/Nostr satellite bridge protocols

**Future Commercial Potential:**
- **Bitcoin Ecosystem Support**: Alternative satellite infrastructure for Bitcoin nodes and Lightning Network
- **Nostr Network Resilience**: Redundant satellite access for decentralized social protocols  
- **Blockstream Complement**: Provides diversity and backup to existing Bitcoin satellite services
- **Global Financial Inclusion**: Satellite-enabled Bitcoin access in underserved regions

The QO-100 R&D phase validates the technical concept and builds the foundational protocols. The commercial phase creates a robust alternative to single-provider Bitcoin satellite solutions.

**Key Value Propositions:**
- **Bitcoin Network Resilience**: Multiple satellite providers prevent single points of failure
- **Nostr Global Reach**: Censorship-resistant social networking via satellite
- **Emergency Bitcoin Access**: Financial transactions when terrestrial networks fail
- **Infrastructure Diversity**: Complement existing services rather than compete directly

---

*Current development focus: Perfecting the HSModem interface and validating end-to-end Bitcoin/Nostr message delivery via QO-100 satellite testbed.*

 
⚡ BTC LN : cryptoice@walletofsatoshi.com
⚡ BTC Onchain: 347ePgUhyvztUWVZ4YZBmBLgTn8hxUFNeQ
