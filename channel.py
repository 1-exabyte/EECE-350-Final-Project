# channel.py -- Member 1: unreliable channel (randomly drops and reorders packets)
# Done by Jean Paul Chaaya.
import random, struct
def unreliable_send(sock, packet, destination, loss, reorder, channel_state):
    if not (loss>=0 and loss<=1):
        raise ValueError("loss must be between 0 and 1.")
    if not (reorder>=0 and reorder<=1):
        raise ValueError("reorder must be between 0 and 1.")
    if loss+reorder>1:
        raise ValueError("loss+reorder must be less than or equal to 1.")
    
    x = random.random()
    packet_type, seq, length = struct.unpack("!BIH", packet[:7])
    if channel_state['held_packet'] is None: #If we didnt have a packet to reorder
        #0->loss ; loss->loss+reorder; loss+reorder->1
        #  DROP           REORDER          SEND
        if x<loss: #DROP
            print(f"DROPPED packet {seq}")
            channel_state["dropped"] += 1
        elif x<loss+reorder: #REORDER
            channel_state['held_packet']=packet
            channel_state["reordered"] += 1
            print(f"HOLD packet {seq}")
        else: 
            sock.sendto(packet, destination)
            channel_state["sent"] += 1
            print(f"SENT packet {seq}")
            
    else: #if we had a packet to reorder
        packet_type2, seq2, length2 = struct.unpack("!BIH", channel_state['held_packet'][:7])
        if x<loss: #Drop it and release held
            print(f"DROPPED packet {seq}")
            channel_state["dropped"] += 1
            sock.sendto(channel_state['held_packet'], destination)
            channel_state["sent"] += 1
            print(f"SENT reordered packet {seq2} after packet {seq} was dropped")
        else: #Send it then release held
            sock.sendto(packet, destination)
            channel_state["sent"] += 1
            print(f"SENT packet {seq}")
            sock.sendto(channel_state['held_packet'], destination)
            channel_state["sent"] += 1
            print(f"SENT  reordered packet {seq2} after packet {seq}")
        channel_state['held_packet']=None

def flush_channel(sock, destination, channel_state):
    if channel_state['held_packet'] is not None:
        packet_type, seq, length = struct.unpack("!BIH", channel_state['held_packet'][:7])
        sock.sendto(channel_state['held_packet'], destination)
        channel_state["sent"] += 1
        print(f"FLUSHED packet {seq}")
        channel_state['held_packet']=None

def print_channel_stats(channel_state):
    print('========== CHANNEL STATISTICS ==========')
    print(f"Packets sent through UDP : {channel_state['sent']}\nPackets dropped          : channel_state['dropped']\nPackets reordered        : {channel_state['reordered']}")