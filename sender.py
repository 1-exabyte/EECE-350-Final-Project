# sender.py -- Member 1: split the file into packets / Member 2: window and timers
import socket

from packets import split_file, make_packet, make_end_packet
from sender_window import run_sender

if __name__ == "__main__":
    filepath = "test_input.txt"
    window_size = 4
    chunks = split_file(filepath, 8)
    packets = []
    for i in range(len(chunks)):
        seq = i
        packets.append(make_packet(0, seq, chunks[seq]))
    packets.append(make_end_packet(filepath, len(chunks)))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_without_loss(packet):
        sock.sendto(packet, ("127.0.0.1", 9000))
    run_sender(packets, window_size, send_without_loss, sock)
    sock.close()
