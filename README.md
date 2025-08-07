# BitSatRelay: Hybrid Bluetooth-Satellite Mesh Communication System

**Project Vision:** Extend BitChat's local Bluetooth LE mesh networking globally via QO-100 satellite links through HSModem integration, creating the world's first hybrid local-global mesh messaging system.

## Project Name: **BitSatRelay**

*Rationale: "Bit" encompasses both BitChat and Bitcoin-style decentralization, "Sat" clearly indicates satellite technology, and "Relay" describes the core function of bridging local and global networks.*

---

## Executive Summary

BitSatRelay integrates two proven technologies:
- **BitChat**: Decentralized Bluetooth LE mesh chat system with end-to-end encryption
- **HSModem**: High-speed satellite modem for QO-100 amateur radio satellite

The result: Local mesh networks that seamlessly extend globally via satellite, providing resilient offgrid communication at a global scale for privacy-conscious users.

---

## Technical Architecture

### Core Components

1. **Transport Abstraction Layer**
   - Unified interface for multiple transport types
   - Bluetooth LE (local, low-power, multi-hop)
   - QO-100 Satellite (global, high-power, single-hop)

2. **Hybrid Routing Engine**
   - Intelligent transport selection based on destination
   - Power-aware routing decisions
   - Automatic failover between transports

3. **Bridge Node System**
   - Devices with both Bluetooth and HSModem capability
   - Automatic gateway functionality
   - Load balancing across multiple bridges

4. **Protocol Translation Layer**
   - BitChat packet format ↔ HSModem UDP interface
   - Message fragmentation/reassembly
   - Encryption boundary management

### Message Flow Architecture
```
Local BLE Mesh ←→ Bridge Node ←→ HSModem ←→ QO-100 ←→ Remote HSModem ←→ Remote Bridge ←→ Remote BLE Mesh
```

---

## Development Phases

### Phase 1: Foundation
**Goal:** Basic transport abstraction and HSModem integration

**Deliverables:**
- Transport protocol interface definition
- HSModem UDP client implementation
- Basic packet translation layer
- Proof-of-concept bridge application

**Success Criteria:**
- Send/receive simple messages via HSModem UDP interface
- Packet format translation working
- Basic BitChat message interception

### Phase 2: Integration
**Goal:** Integrate with BitChat's existing codebase

**Deliverables:**
- Modified BitChat with transport abstraction
- QO-100 transport implementation
- Basic routing engine
- Multi-transport peer discovery

**Success Criteria:**
- Two BitChat instances communicate via satellite
- Automatic transport selection working
- Peer discovery across transports

### Phase 3: Hybrid Mesh
**Goal:** Full hybrid mesh implementation

**Deliverables:**
- Smart routing algorithms
- Bridge node auto-discovery
- Global channel federation
- Power management integration
- User interface enhancements

**Success Criteria:**
- Seamless local-to-global message routing
- Multiple bridge nodes load balancing
- Battery-efficient operation
- Transparent user experience

---

## Critical Technical Questions

### BitChat Integration Questions
1. **Message Storage Access**: How does BitChat store messages internally? SQLite database? Core Data? In-memory only?
2. **Packet Format**: What's the exact binary format of BitchatPacket? How are they serialized/deserialized?
3. **Routing Hooks**: Where in BitChat's code can we intercept outgoing messages and inject incoming ones?
4. **Peer Management**: How does BitChat maintain its peer list? Can we add "virtual" satellite peers?
5. **Transport Abstraction**: Does BitChat's architecture allow for transport abstraction, or is Bluetooth LE deeply embedded?

### HSModem Integration Questions
1. **Discovery Mechanism**: How do we discover remote HSModem instances on the QO-100 network?
2. **Addressing Scheme**: How do we identify/address remote nodes in the satellite network?
3. **Message Routing**: Does HSModem handle any routing, or is it point-to-point only?
4. **Bandwidth Management**: What's the practical message throughput we can achieve?
5. **Error Handling**: How does HSModem handle transmission failures, and how should we retry?

### Protocol Questions
1. **Encryption Boundaries**: Should messages be encrypted end-to-end across both transports, or per-transport?
2. **Message Fragmentation**: How do we handle BitChat messages larger than HSModem's 219-byte payload?
3. **TTL Management**: How do we manage TTL across different transport types with different hop limits?
4. **Duplicate Detection**: How do we prevent message loops between Bluetooth and satellite paths?
5. **Network Partitioning**: What happens when satellite links are down? How do we handle split-brain scenarios?

### User Experience Questions
1. **Transport Visibility**: Should users see which transport their messages use, or keep it transparent?
2. **Network Status**: How do we indicate satellite connectivity status in the UI?
3. **Power Management**: Should users control when satellite transport is active?
4. **Configuration**: What HSModem parameters need user configuration vs. auto-discovery?

---

## Technical Challenges & Risks

### High Priority Challenges

1. **BitChat Code Analysis**
   - *Challenge*: Understanding BitChat's internal architecture without extensive documentation
   - *Risk*: Significant architectural changes needed
   - *Mitigation*: Start with external bridge approach, gradually integrate

2. **Protocol Translation**
   - *Challenge*: Mapping BitChat's packet format to HSModem's UDP interface
   - *Risk*: Message loss or corruption during translation
   - *Mitigation*: Implement comprehensive packet validation and retry logic

3. **Timing Synchronization**
   - *Challenge*: Bluetooth LE (~100ms) vs Satellite (~600ms) latency differences
   - *Risk*: Message ordering issues and timeout problems
   - *Mitigation*: Adaptive timeout algorithms and sequence numbering

### Medium Priority Challenges

4. **Power Management**
   - *Challenge*: HSModem transmission is power-hungry vs BitChat's efficiency focus
   - *Risk*: Rapid battery drain on mobile devices
   - *Mitigation*: Smart routing to minimize satellite usage

5. **Network Discovery**
   - *Challenge*: Different discovery mechanisms for Bluetooth vs satellite
   - *Risk*: Inconsistent peer visibility
   - *Mitigation*: Unified peer management with transport tagging

6. **Message Ordering**
   - *Challenge*: Messages may arrive out-of-order across different transports
   - *Risk*: Conversation coherence issues
   - *Mitigation*: Timestamp-based ordering with transport latency compensation

### Lower Priority Challenges

7. **Amateur Radio Regulations**
   - *Challenge*: Ensuring compliance with amateur radio rules on QO-100
   - *Risk*: Regulatory issues if used improperly
   - *Mitigation*: Clear documentation and optional callsign integration

8. **Scalability**
   - *Challenge*: Performance with many bridge nodes and high message volumes
   - *Risk*: Network congestion and slow message delivery
   - *Mitigation*: Load balancing algorithms and traffic shaping

---

## Success Metrics

### Technical Metrics
- **Message Delivery Rate**: >99% for local, >95% for satellite
- **Latency**: <200ms local, <2s satellite (including retry)
- **Battery Impact**: <20% increase in power consumption
- **Network Efficiency**: <10% duplicate messages across transports

### User Experience Metrics
- **Setup Time**: <5 minutes for basic configuration
- **Transport Transparency**: Users shouldn't need to think about routing
- **Reliability**: System gracefully handles transport failures
- **Compatibility**: Works with existing BitChat installations

---

## Development Environment Setup

### Required Tools
- **Xcode**: For BitChat iOS development
- **Android Studio**: For BitChat Android development
- **HSModem**: Running instance for testing
- **QO-100 Access**: Either real satellite or simulation

### Testing Strategy
1. **Unit Tests**: Individual transport implementations
2. **Integration Tests**: Cross-transport message delivery
3. **Field Tests**: Real-world satellite communication
4. **Performance Tests**: Battery life and message throughput
5. **Compatibility Tests**: Various BitChat versions and HSModem configurations

---

## Open Questions for Research

1. **BitChat Fork Strategy**: Should we fork BitChat or try to contribute upstream?
2. **Hardware Requirements**: What's the minimum hardware needed for bridge nodes?
3. **Network Topology**: How do we handle multiple satellite uplinks in the same area?
4. **Message Persistence**: How long should messages be cached for offline peers?
5. **Error Recovery**: What's the best strategy for handling partial message delivery?
6. **Security Model**: How do we maintain BitChat's security properties across transports?
7. **Bandwidth Optimization**: Can we compress BitChat messages for satellite transmission?
8. **Geographic Routing**: Should we consider geographic information for routing decisions?

---

## Use Cases & Applications

### Privacy-Conscious Networks
- **Local meetings** use BLE-only mode for security
- **Global coordination** via satellite for planned communications
- **User controls** which messages go via which transport
- **No central servers or tracking**

### Ham Radio Evolution
- **Modern mesh chat** for amateur radio operators
- **Leverages existing QO-100** amateur radio satellite infrastructure
- **Bridges traditional radio** with modern mobile devices
- **Compliant with amateur radio regulations**

### Emergency Response
- **Field teams** coordinate via local Bluetooth mesh
- **Command center** maintains satellite uplink for global coordination
- **Messages flow seamlessly** between field operations and headquarters
- **Works when cellular/internet infrastructure fails**

### Remote Operations
- **Expedition teams** use local mesh for team coordination
- **Base station** provides satellite link to home base/weather services
- **Automatic switching** based on distance from base camp
- **Maintains communication in remote areas**
---

## Next Steps

1. **Phase 1 Research**: Analyze BitChat source code structure and message flow
2. **HSModem Setup**: Set up HSModem development environment and basic UDP client
3. **Proof of Concept**: Create proof-of-concept packet translation layer
4. **Interface Design**: Design transport abstraction interface
5. **Bridge Implementation**: Implement basic bridge application
6. **Testing**: Test basic message passing via HSModem
7. **Documentation**: Document findings and refine architecture plan

---

## Resources & References

- **BitChat Repository**: https://github.com/permissionlesstech/bitchat
- **BitChat Android**: https://github.com/permissionlesstech/bitchat-android
- **HSModem Manual**: Downloaded PDF with UDP interface documentation
- **QO-100 Information**: Amateur radio satellite technical specifications
- **Noise Protocol**: BitChat's encryption framework documentation
- **Amateur Radio Regulations**: Relevant rules for satellite operation
- **AMSAT-DL**: QO-100 satellite operator organization

---

## Contributing

I am taking on a monster challenge here as a hardware engineer - So I  welcome contributions from developers, ham radio operators, and anyone interested in advancing decentralized communication technology. Key areas where help is needed: pretty much on all aspects. 

- **BitChat Analysis**: Understanding the codebase and architecture
- **HSModem Integration**: UDP interface development and testing
- **Protocol Design**: Packet translation and routing algorithms
- **Testing**: Field testing with real QO-100 equipment
- **Documentation**: Technical documentation and user guides

Wish me luck ! 
 
⚡ BTC LN : cryptoice@walletofsatoshi.com
⚡ BTC Onchain: 347ePgUhyvztUWVZ4YZBmBLgTn8hxUFNeQ
