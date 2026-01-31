#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

root_bridge_id = 0x0
root_path_cost = 0
root_port_index = 0
lock = threading.Lock()   

def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]

    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    vlan_tci = -1
    # Check for VLAN tag (0x8200 in network byte order is b'\x82\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id, vlan_tci

def parse_PPDU_header(data):
    # Dam parse doar la ce ne intereseaza
    dest_mac = data[0:6]
    src_mac  = data[6:12]

    ppdu_config = data[25:]

    root_bridge_id_local = ppdu_config[1:9]
    root_path_cost_local = int.from_bytes(ppdu_config[9:13], "big")
    port_id_local        = int.from_bytes(ppdu_config[17:19], "big")

    #print(f"Read root {root_bridge_id_local}")

    return dest_mac, src_mac, root_bridge_id_local, root_path_cost_local, port_id_local



def read_config(id):
    config_file = "./configs/switch" + str(id) + ".cfg"
    first = False
    priority = 0
    interfaces = []
    with open(config_file, "r") as file:
        for line in file:
            content = line.strip().split()
            if first == False:
                priority = content[0]
                first = True
            else:
                if content[1] == 'T':
                    interfaces.append(content[1])
                else:
                    interfaces.append(int(content[1])) 
    return priority,interfaces            


def nibble_creator(src_mac):
    sum = 0
    for b in src_mac:
        sum += (b>>4)
        sum += (b & 0xF)
    return sum & 0xF    

def create_vlan_tag(ext_id, vlan_id):
    # Use EtherType = 8200h for our custom 802.1Q-like protocol.
    # PCP and DEI bits are used to extend the original VID.
    #
    # The ext_id should be the sum of all nibbles in the MAC address of the
    # host attached to the _access_ port. Ignore the overflow in the 4-bit
    # accumulator.
    #
    # NOTE: Include these 4 extensions bits only in the check for unicast
    #       frames. For multicasts, assume that you're dealing with 802.1Q.
    return struct.pack('!H', 0x8200) + \
           struct.pack('!H', ((ext_id & 0xF) << 12) | (vlan_id & 0x0FFF))

def function_on_different_thread():
    while True:
        time.sleep(1)

def is_unicast(mac):
    return (mac[0] & 1) == 0

def send_HPDU(interfaces):
    dest_mac = b"\xff\xff\xff\xff\xff\xff"
    src_mac = get_switch_mac()
    ether_type = (0x0800).to_bytes(2, "big")
    payload = b"\xff"

    data = dest_mac + src_mac + ether_type + payload

    while True:
        for i in interfaces:
            send_to_link(i, len(data), data)
        time.sleep(1)

def send_PPDU(interfaces, vlan_interfaces, seq_number, root_cost_local, root_bridge_id_local, priority):
    dest_mac = b"\x01\x80\xC2\x00\x00\x00"
    src_mac = get_switch_mac()
    llc_header = b"\x42\x42\x03"

    protocol_id      = (0x0002).to_bytes(2,"big")
    protocol_version = (0).to_bytes(1,"big")
    ppdu_type        = (0x80).to_bytes(1,"big")
    seq_number_bytes = (seq_number % 100).to_bytes(4,"big")
    ppdu_header = protocol_id + protocol_version + ppdu_type + seq_number_bytes

    flags = (0).to_bytes(1,"big")
    root_path_cost_bytes = (root_cost_local).to_bytes(4,"big")
    bridge_id = int((priority)).to_bytes(2,"big") + src_mac

    message_age    = (0).to_bytes(2,"big")
    max_age        = (40).to_bytes(2,"big")
    hello_time     = (2).to_bytes(2,"big")
    forward_delay  = (4).to_bytes(2,"big")

    #print(f"Sending PPDU with root as: {root_bridge_id_local}")

    for i in interfaces:
        if vlan_interfaces[i] == 'T':
            port_priority = 128
            port_id = ((port_priority << 8) | i).to_bytes(2, "big")

            ppdu_config = (
                flags + root_bridge_id_local + root_path_cost_bytes + bridge_id +
                port_id + message_age + max_age + hello_time + forward_delay
            )

            llc_length = (len(llc_header) + len(ppdu_header) + len(ppdu_config)).to_bytes(2,"big")
            data = dest_mac + src_mac + llc_length + llc_header + ppdu_header + ppdu_config
            send_to_link(i, len(data), data)

def send_PPDU_thread(interfaces, vlan_interfaces, priority):
    seq_number = 0
    while True:
        with lock:
            global root_bridge_id, root_path_cost, root_port_index
            current_root_id = root_bridge_id
            current_root_cost = root_path_cost

        send_PPDU(interfaces, vlan_interfaces, seq_number, current_root_cost, current_root_id, priority)
        seq_number = seq_number + 1
        # 2 = hello time ul
        time.sleep(2)          


def main():
    global root_bridge_id, root_path_cost, root_port_index
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]



    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    # Citim config file ul asociat switch ului nostru 
    priority,interfaces_vlan = read_config(switch_id)
    port_states = [1] * num_interfaces

    #print("# Starting switch with id {}".format(switch_id), flush=True)
    #print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))
    root_path_cost = 0
    root_bridge_id = int(priority).to_bytes(2,"big") + get_switch_mac()


    # Rulam HDPU senderul pe alt thread ca sa nu ne bocheze switchul
    t1 = threading.Thread(target=send_HPDU,args=(interfaces,),daemon=True)
    t1.start()
    # Rulam PPDU sender ul pe alt thread acuma
    t2 = threading.Thread(target=send_PPDU_thread, args=(interfaces, interfaces_vlan, priority), daemon=True)
    t2.start()

    # Initializam tabela CAM
    cam = {}
    

    #print(f"[INFO] interfaces_vlan = {interfaces_vlan}")
    #for i, v in enumerate(interfaces_vlan):
        #print(f"[INFO] Interface {i}: VLAN = {v}")

    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].

        interface, data, length = recv_from_any_link()

        # Verificam daca e PPDU
        if data[14:17] == b"\x42\x42\x03":
            dest_mac, src_mac, root_id_received, root_cost_received, port_id_received = parse_PPDU_header(data)
            #print(f"Received PPDU from root: {root_id_received.hex()}")

            if dest_mac == b"\x01\x80\xC2\x00\x00\x00":
                with lock:
                    # Root ID-ul local și Path Cost-ul local
                    local_bridge_id_bytes = int(priority).to_bytes(2, "big") + get_switch_mac()
                    local_bridge_id_int = int.from_bytes(local_bridge_id_bytes, "big")
                    current_root_int = int.from_bytes(root_bridge_id, "big")

                    # Root ID primit și path cost calculat
                    root_id_received_int = int.from_bytes(root_id_received, "big")
                    new_cost = root_cost_received + 19

                    if root_id_received_int < current_root_int:
                        root_bridge_id = root_id_received
                        root_path_cost = new_cost
                        root_port_index = interface

                    elif root_id_received_int == current_root_int:
                        if new_cost < root_path_cost:
                            root_path_cost = new_cost
                            root_port_index = interface
                        elif new_cost == root_path_cost:
                            # Comparăm sender bridge ID (priority + MAC)
                            sender_bridge_id_bytes = int(priority).to_bytes(2,"big") + src_mac
                            sender_bridge_id_int = int.from_bytes(sender_bridge_id_bytes, "big")
                            if sender_bridge_id_int < local_bridge_id_int:
                                root_port_index = interface

                    #print(f"[INFO] Current Root: {root_bridge_id.hex()}, Path Cost: {root_path_cost}, Root Port: {root_port_index}")

                # Updatam porturile
                for j in range(num_interfaces):
                    if j == root_port_index or root_bridge_id == int(priority).to_bytes(2,"big") + get_switch_mac():
                        port_states[j] = 1
                    elif interfaces_vlan[j] == 'T':
                        port_states[j] = 0
                    else:
                        port_states[j] = 1

                continue

        if(port_states[interface] == 0):
            #print("Nu e bun asta")
            continue
        
        dest_mac, src_mac, ethertype, vlan_id, vlan_tci = parse_ethernet_header(data)

        nibble = nibble_creator(src_mac)

        nibble_dest = nibble_creator(dest_mac)


        # #print the MAC src and MAC dst in human readable format
        # Am schimbat pt ca ma enerveaza erau string
        dest_mac_print = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac_print = ':'.join(f'{b:02x}' for b in src_mac)

        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(5, 10) + data[12:]

        #print(f'Destination MAC: {dest_mac_print}')
        #print(f'Source MAC: {src_mac_print}')
        #print(f'EtherType: {ethertype}')

        #print("Received frame of size {} on interface {}".format(length, interface), flush=True)


        # TODO: Implement forwarding with learning
        # Adaugam in cam table port + mac

        if port_states[interface] == 1:
            cam[src_mac] = interface


        # Verificam vlanul interfetei sursa
        src_vlan = interfaces_vlan[interface]

        # Daca e HDPU
        if dest_mac == b"\xff\xff\xff\xff\xff\xff" and ethertype == 0x0800 and data[14:] == b"\xff":
            continue

        # Daca vine de pe un acces setam vlan id ul cu vlan id ul portului
        if vlan_id == -1:
            vlan_id = src_vlan


        # Daca a venit de pe un Trunk => trimitem doar pe interfete cu vlanul din packet ul primit sau pe alte trunkuri
        if src_vlan == 'T':
            # Trb sa cream un packet pt acces ports cu data si len nou
            data_access = data[0:12] + data[16:]
            length_acces = length - 4
            #print(f"[DEBUG] Trunk → Access: src_vlan=T, vlan_id={vlan_id}, data_access length={len(data_access)}")

            if is_unicast(dest_mac):
                if dest_mac in cam:
                    dst_vlan = interfaces_vlan[cam[dest_mac]]
                    # Verificam nibble ul la packet
                    tci_ext = (vlan_tci >> 12) & 0xF
                    if tci_ext != nibble_dest and interfaces_vlan[cam[dest_mac]] != 'T':
                        #print(f"[DEBUG] Nibble mismatch → drop frame to {dest_mac}")
                        continue
                    #print(f"[DEBUG] Unicast to learned dest {dest_mac} on interface {cam[dest_mac]}, VLAN={dst_vlan}")
                    if dst_vlan == vlan_id:
                        send_to_link(cam[dest_mac], length_acces, data_access)
                    elif dst_vlan == 'T' and port_states[cam[dest_mac]] == 1:
                        send_to_link(cam[dest_mac], length, data)
                else:
                    #print(f"[DEBUG] Unicast dest {dest_mac} unknown → flooding")
                    for i in interfaces:
                        if i != interface:
                            if interfaces_vlan[i] == 'T' and port_states[i] == 1:
                                send_to_link(i, length, data)
                            elif interfaces_vlan[i] == vlan_id:
                                send_to_link(i, length_acces, data_access)
            else:
                #print(f"[DEBUG] Broadcast/multicast frame → flooding")
                for i in interfaces:
                    if i != interface:
                        if interfaces_vlan[i] == 'T' and port_states[i] == 1:
                            send_to_link(i, length, data)
                        elif interfaces_vlan[i] == vlan_id:
                            #print(f"[DEBUG] Sent to {i}")
                            send_to_link(i, length_acces, data_access)

        else:
            # Trb sa cream un packet nou pt trunk ports
            data_trunk = data[0:12] + create_vlan_tag(nibble, interfaces_vlan[interface]) + data[12:]
            length_trunk = length + 4
            #print(f"[DEBUG] Access → Trunk: interface {interface}, data_trunk length={len(data_trunk)}")

            if is_unicast(dest_mac):
                if dest_mac in cam:
                    dst_vlan = interfaces_vlan[cam[dest_mac]]
                    tci_ext = (vlan_tci >> 12) & 0xF
                    if tci_ext != nibble_dest and interfaces_vlan[cam[dest_mac]] != 'T':
                        #print(f"[DEBUG] Nibble mismatch → drop frame to {dest_mac}")
                        continue
                    #print(f"[DEBUG] Unicast to learned dest {dest_mac} on interface {cam[dest_mac]}, VLAN={dst_vlan}")
                    if dst_vlan == vlan_id:
                        send_to_link(cam[dest_mac], length, data)
                    elif dst_vlan == 'T' and port_states[cam[dest_mac]] == 1:
                        send_to_link(cam[dest_mac], length_trunk, data_trunk)
                else:
                    #print(f"[DEBUG] Unicast dest {dest_mac} unknown → flooding")
                    for i in interfaces:
                        if i != interface:
                            if interfaces_vlan[i] == 'T' and port_states[i] == 1:
                                send_to_link(i, length_trunk, data_trunk)
                            elif interfaces_vlan[i] == vlan_id:
                                send_to_link(i, length, data)
            else:
                #print(f"[DEBUG] Broadcast/multicast frame → flooding")
                for i in interfaces:
                    if i != interface:
                        if interfaces_vlan[i] == 'T' and port_states[i] == 1:
                            #print(f"[DEBUG] Sent on interface {i}")
                            send_to_link(i, length_trunk, data_trunk)
                        elif interfaces_vlan[i] == vlan_id:
                            #print(f"[DEBUG] Sent on interface {i}")
                            send_to_link(i, length, data)
            
        # TODO: Implement VLAN support
        # TODO: Implement STP support

        # data is of type bytes.
        # send_to_link(i, length, data)

if __name__ == "__main__":
    main()
