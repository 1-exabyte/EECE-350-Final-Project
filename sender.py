# sender.py -- Member 1: split the file into packets / Member 2: window and timers
import socket
import random
import os
from channel import unreliable_send, flush_channel, print_channel_stats
from packets import split_file, make_packet, make_end_packet
from sender_window import run_sender


if __name__ == "__main__":  # member 2 test
    filepath = "test_input.txt"
    window_size = 4
    chunks = split_file(filepath, 8)
    packets = []
    for i in range(len(chunks)):
        seq = i
        packets.append(make_packet(0, seq, chunks[seq]))
    packets.append(make_end_packet(filepath, len(chunks)))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    destination = ("127.0.0.1", 9000)
    loss = 0.1
    reorder = 0.2
    random.seed(37)

    channel_state = {
        "held_packet": None,
        "sent": 0,
        "dropped": 0,
        "reordered": 0
    }

    print("File:", filepath, "Size:", os.path.getsize(filepath), "bytes")
    print("DATA packets:", len(chunks), "END packets:", 1)
    print("Window:", window_size, "Loss:", loss, "Reorder:", reorder)

    def send_via_channel(packet):
        unreliable_send(
            sock, packet, destination, loss, reorder, channel_state
        )

        if packet == packets[-1]:
            flush_channel(sock, destination, channel_state)

    run_sender(packets, window_size, send_via_channel, sock)

    flush_channel(sock, destination, channel_state)
    print_channel_stats(channel_state)
    sock.close()
