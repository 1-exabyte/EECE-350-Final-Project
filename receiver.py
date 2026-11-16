# receiver.py -- Member 3 (Andrew Samaha): receiver and acknowledgements
#
# Packet header (agreed by the group):  type (1 byte) | seq (4 bytes) | length (2 bytes) | data
#   type 0 = DATA   type 1 = ACK   type 2 = END (data = SHA-256 of the file)
#
# Every ACK carries "expected" = the number of the next packet I need.
#
# Run:  python receiver.py              (port 9000, writes received.txt)
#       python receiver.py 9000 out.bin (port, output file)

import hashlib
import socket
import struct
import sys
import time
#############################################################################################################################
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"
RESET  = "\033[0m"
#############################################################################################################################
DATA = 0
ACK = 1
END = 2

port = 9000
out_file = "received.txt"
if len(sys.argv) > 1:
    port = int(sys.argv[1])
if len(sys.argv) > 2:
    out_file = sys.argv[2]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", port))

print("========== RECEIVER (Member 3) ==========")
print(f"Listening on port : {port}")
print(f"Output file       : {out_file}")
print("=========================================")

expected = 0        # next packet number I need
buffer = {}         # packets that came early:  seq -> data
chunks = []         # the file, in order
end_seq = None      # number of the END packet, once it arrives
end_hash = None     # SHA-256 sent inside END

# counters for the summary
received = 0
in_order = 0
out_of_order = 0
gap_fills = 0
duplicates = 0
start_time = None


def glue(data):
    chunks.append(data)              # add this piece to the end of the file


def send_ack():
    sock.sendto(struct.pack("!BIH", ACK, expected,0), addr)


while True:
    try:
        data, addr = sock.recvfrom(65535)
    except ConnectionResetError:        # Windows quirk when the sender closes: ignore it
        continue

    if len(data) < 7:
        print(f"{RED}BAD packet ({len(data)} bytes) --skipped--{RESET}")
        continue

    ptype, seq, length = struct.unpack("!BIH", data[:7]) 
    payload = data[7:7+length]
    if ptype not in (DATA,  END) or len(payload) != length:
        print(f"{RED}BAD packet (type {ptype}, seq {seq}) --skipped--{RESET}")
        continue

    received += 1
    if start_time is None:
        start_time = time.time()

    # ---- END packet: remember where the file ends and its fingerprint (never glued)
    if ptype == END:
        end_seq = seq
        end_hash = payload
        if expected < seq:
            print(f"{YELLOW}RECV END({seq}) early -> DUP ACK {expected}{RESET}")
        else:
            print(f"RECV END({seq}) -> file has {seq} packets")

    # ---- in order: glue it, then glue everything in the buffer that now follows
    elif seq == expected:
        glue(payload)
        expected += 1
        first = seq
        while expected in buffer:
            glue(buffer.pop(expected))
            expected += 1
        if expected - first == 1:
            in_order += 1
            print(f"{GREEN}RECV {seq} in order -> ACK {expected}{RESET}")
        else:
            gap_fills += 1
            print(f"{CYAN}RECV {seq} fills gap -> ACK {expected}   (glued {first} to {expected - 1}){RESET}")

    # ---- duplicate: already glued, or already waiting in the buffer
    elif seq < expected or seq in buffer:
        duplicates += 1
        print(f"{RED}RECV {seq} duplicate, discarded -> ACK {expected} (re-sent){RESET}")

    # ---- out of order: came early, keep it for later
    else:
        buffer[seq] = payload
        out_of_order += 1
        print(f"{YELLOW}RECV {seq} out of order, buffered -> DUP ACK {expected}   buffer={sorted(buffer)}{RESET}")

    # ---- every data packet is here -> count END as received, finish
    if end_seq is not None and expected == end_seq:
        expected += 1
        send_ack()
        print(f"{GREEN}ACK {expected} (END received){RESET}")
        end_time = time.time()
        sock.settimeout(2.0)
        while True:
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                break
            except ConnectionResetError:        # Windows quirk when the sender closes: ignore it
                continue
            if len(data) >=7:
                send_ack()
                print(f"{RED}RECV repeated packet -> ACK {expected} (re-sent){RESET}")
        break
    send_ack()

# ---- write the file, then check it against the SHA-256 from END
file_data = b"".join(chunks)
with open(out_file, "wb") as f:
    f.write(file_data)
with open(out_file, "rb") as f:
    match = hashlib.sha256(f.read()).digest() == end_hash

print("================ SUMMARY ================")
print(f"Packets received        : {received}")
print(f"{GREEN}  in order              : {in_order}{RESET}")
print(f"{YELLOW}  out of order (buffer) : {out_of_order}{RESET}")
print(f"{CYAN}  filled a gap          : {gap_fills}{RESET}")
print(f"{RED}  duplicates discarded  : {duplicates}{RESET}")
print(f"File written            : {out_file} ({len(file_data)} bytes)")
print(f"Transfer time           : {end_time - start_time:.3f} s")
if match:
    result = f"{GREEN}MATCH{RESET}"
else:
    result = f"{RED}MISMATCH{RESET}"
print(f"SHA-256 check           : {result}")
print("=========================================")
