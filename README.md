Ethernet Switch with VLAN and PSTP
Overview

This project implements a software-based Ethernet switch in Python, developed and tested using Mininet.
The switch supports:

MAC learning and frame forwarding

Custom VLAN tagging (Poli VLAN – 802.1Q-like)

Simplified Spanning Tree Protocol (PSTP)

The goal is to simulate real Layer 2 switch behavior, including loop prevention and VLAN isolation.

Features
1. MAC Learning & Forwarding

Learns source MAC addresses and associates them with input ports (CAM table).

Forwards unicast frames to known destinations.

Floods unknown unicast and broadcast frames.

Drops frames received on blocked ports (STP state).

2. VLAN Support (Poli VLAN Tagging)

Custom VLAN tagging protocol similar to IEEE 802.1Q:

TPID: 0x8200

VLAN ID: 12 bits (configured per port)

Upper 4 bits of TCI: sum of MAC address nibbles (used for validation)

Frame size increases by 4 bytes when tagged

Port Types:

Access ports:

Connect hosts

Frames are sent untagged

VLAN is determined by port configuration

Trunk ports:

Connect switches

Frames are transmitted with VLAN tag

Carry traffic from multiple VLANs

VLAN forwarding rules:

Access → Trunk: add VLAN tag

Trunk → Access: remove VLAN tag

Forward only within same VLAN (or trunk ports)

3. PSTP (Poli Spanning Tree Protocol)

Simplified implementation of IEEE 802.1D Spanning Tree:

Implemented Components:

HPDU (Hello Protocol Data Unit):

Sent every second

Ethernet type 0x0800

Broadcast destination MAC

PPDU (Poli Protocol Data Unit):

Custom BPDU-like packet using LLC header (DSAP=0x42, SSAP=0x42)

Contains: Root Bridge ID, Sender Bridge ID, Root Path Cost, Port ID, Sequence number modulo 100

STP Behavior:

Each switch initially considers itself root.

Root election based on lowest Bridge ID.

Root path cost updated dynamically.

Ports can be:

Forwarding

Blocking

Only trunk ports are blocked when needed to eliminate loops.

One global spanning tree for all VLANs.

Configuration

Each switch reads a configuration file:

<priority>
<interface_id> <VLAN_ID | T>


T → trunk port

number → access port with that VLAN

Example:

10
0 1
1 T
2 2

How to Run

Start Mininet topology:

sudo python3 topo.py


Start each switch:

python3 switch.py <switch_id> <interfaces...>


Test connectivity:

ping hostX


Use Wireshark to inspect:

VLAN tagging (TPID 0x8200)

PPDU frames

HPDU frames

Design Decisions

CAM table implemented using a Python dictionary.

STP state stored per-port using a port_states list.

Global root information protected with a threading lock.

PPDU sending runs in a separate thread (hello timer = 2s).

Cost per link set to 19 (100 Mbps, according to 802.1D).

Limitations

Single spanning tree for all VLANs.

No port state transitions (Listening/Learning not implemented).

No link failure detection (HPDU only sent, not processed).

Testing

Manual testing using ping

Wireshark inspection of VLAN tags and PPDU frames

Automated checker provided in assignment
