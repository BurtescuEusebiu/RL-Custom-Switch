# Ethernet Switch with VLAN and PSTP

## Overview

This project implements a software-based Ethernet switch in Python, developed and tested using Mininet. The switch simulates real Layer 2 switch behavior, including MAC learning, frame forwarding, loop prevention via Spanning Tree Protocol, and VLAN isolation.

## Features

### 1. MAC Learning and Forwarding
- **CAM Table:** Learns source MAC addresses and associates them with input ports using a Python dictionary.
- **Forwarding Logic:**
  - Forwards unicast frames to known destinations.
  - Floods unknown unicast and broadcast frames to all active ports.
  - Drops frames received on ports blocked by STP.

### 2. VLAN Support (Poli VLAN Tagging)
Implements a custom VLAN tagging protocol similar to IEEE 802.1Q.

- **Tag Structure:**
  - **TPID:** 0x8200
  - **VLAN ID:** 12 bits (configured per port)
  - **TCI Upper 4 Bits:** Sum of MAC address nibbles (used for validation)
  - **Frame Size:** Increases by 4 bytes when tagged

- **Port Types:**
  - **Access Ports:** Connect to hosts. Frames are sent untagged. VLAN is determined by port configuration.
  - **Trunk Ports:** Connect to switches. Frames are transmitted with VLAN tags. Carry traffic from multiple VLANs.

- **Forwarding Rules:**
  - **Access to Trunk:** Add VLAN tag.
  - **Trunk to Access:** Remove VLAN tag.
  - **Isolation:** Forward only within the same VLAN (or via trunk ports).

### 3. PSTP (Poli Spanning Tree Protocol)
A simplified implementation of IEEE 802.1D Spanning Tree Protocol.

- **Protocol Data Units:**
  - **HPDU (Hello Protocol Data Unit):** Sent every second. Ethernet type 0x0800. Broadcast destination MAC.
  - **PPDU (Poli Protocol Data Unit):** Custom BPDU-like packet using LLC header (DSAP=0x42, SSAP=0x42). Contains Root Bridge ID, Sender Bridge ID, Root Path Cost, Port ID, and Sequence number (modulo 100).

- **STP Behavior:**
  - Each switch initially considers itself the root.
  - Root election based on lowest Bridge ID.
  - Root path cost updated dynamically (Cost per link set to 19, representing 100 Mbps per 802.1D).
  - **Port States:** Forwarding or Blocking.
  - Only trunk ports are blocked when necessary to eliminate loops.
  - One global spanning tree is used for all VLANs.

## Configuration

Each switch reads a configuration file to determine priority and port roles.

**File Format:**
```text
<priority>
<interface_id> <VLAN_ID | T>
```



