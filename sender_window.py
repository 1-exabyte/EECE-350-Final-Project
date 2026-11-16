# Jinan Sief El Deen
# Member 2: sending window, ACK handling, and retransmissions
import time
import struct
import socket


def fill_window(packets, base, next_seq, window_size, send_packet, state, send_time, stats):
    while next_seq < len(packets) and next_seq < base+window_size:

        print("SEND", next_seq)
        send_time[next_seq] = time.monotonic()
        send_packet(packets[next_seq])
        state[next_seq] = "S"
        stats["transmissions"] += 1
        next_seq += 1
    return next_seq


def process_ack(base, next_seq, ack_num, dup_count, packets, send_packet, state, send_time, stats):

    if base < ack_num and ack_num <= next_seq:
        for i in range(base, ack_num):
            state[i] = "A"
        base = ack_num
        dup_count = 0
        print("ACK ", ack_num, ", slide window, base =", base)
        # ACK 4 -> slide window, base = 4
    elif ack_num == base and base < next_seq:
        dup_count += 1
        print("DUP ACK ", ack_num, "(", dup_count, ")")

        if dup_count == 3:
            print("3 DUP ACKS, fast retransmit")
            retransmit(base, packets, send_packet, state, send_time, stats)
    return base, dup_count


def retransmit(seq_num, packets, send_packet, state, send_time, stats):

    print("RETRANSMIT", seq_num)
    send_packet(packets[seq_num])

    state[seq_num] = "R"
    send_time[seq_num] = time.monotonic()

    stats["transmissions"] += 1
    stats["retransmissions"] += 1


def has_timed_out(base, next_seq, timer_started, now, timeout):
    if base == next_seq or timer_started is None:
        # are any packets waiting for acks or is a timer running->so false
        return False

    return now - timer_started >= timeout  # simple :)


def update_timeout(sample_rtt, estimated_rtt, deviation):
    if estimated_rtt is None:
        estimated_rtt = sample_rtt
        deviation = sample_rtt/2
    else:
        deviation = 0.75*deviation+0.25*abs(estimated_rtt-sample_rtt)
        estimated_rtt = 0.875 * estimated_rtt + 0.125 * sample_rtt
    new_timeout = max(1.0, estimated_rtt + max(0.001, 4 * deviation))
    return estimated_rtt, deviation, new_timeout


def show_window(base, window_size, state):
    colors = {  # Used ai to know how to do this
        "-": "\033[90m",
        "S": "\033[33m",
        "A": "\033[32m",
        "R": "\033[31m"
    }

    right = min(base + window_size, len(state))
    left = max(0, base - window_size)

    print("WINDOW:", list(range(base, right)))
    print("Recent states:", end=" ")

    for i in range(left, right):
        print(colors[state[i]] + str(i) + ":" + state[i] + "\033[0m", end=" ")

    print()


def run_sender(packets, window_size, send_packet, ack_socket, timeout=1.0):
    base, next_seq, dup_count = 0, 0, 0
    state = ["-" for i in range(len(packets))]
    send_time = {}
    stats = {"transmissions": 0, "retransmissions": 0, "timeouts": 0}
    timer_started = None
    started = time.monotonic()
    ack_socket.settimeout(0.05)
    estimated_rtt = None
    deviation = None
    while base < len(packets):
        if base == next_seq:
            timer_started = time.monotonic()
        old_next = next_seq
        next_seq = fill_window(
            packets, base, next_seq, window_size, send_packet, state, send_time, stats)

        old_base = base
        old_retrans = stats["retransmissions"]
        try:
            data, address = ack_socket.recvfrom(65535)
        except (socket.timeout, ConnectionResetError):
            data = None
        if data is not None and len(data) == 7:
            packet_type, ack_num, length = struct.unpack("!BIH", data)

            if packet_type == 1 and length == 0:
                if base < ack_num and ack_num <= next_seq:
                    rtt_safe = True
                    for i in range(base, ack_num):
                        if state[i] != "S":
                            rtt_safe = False
                            break
                    if rtt_safe:
                        sample_rtt = time.monotonic() - send_time[ack_num - 1]

                        estimated_rtt, deviation, timeout = update_timeout(
                            sample_rtt, estimated_rtt, deviation
                        )

                        print("RTT:", sample_rtt, "timeout:", timeout)
                base, dup_count = process_ack(
                    base, next_seq, ack_num, dup_count,
                    packets, send_packet, state, send_time, stats
                )

        if base != old_base or stats["retransmissions"] > old_retrans:
            if base < next_seq:
                timer_started = time.monotonic()
            else:
                timer_started = None

        if has_timed_out(
            base, next_seq, timer_started, time.monotonic(), timeout
        ):
            print("TIMEOUT", base)
            stats["timeouts"] += 1

            retransmit(
                base, packets, send_packet, state, send_time, stats
            )
            timeout *= 2
            print("Timeout backed off to", timeout, "seconds")
            timer_started = time.monotonic()
            dup_count = 0
        if next_seq != old_next or base != old_base or stats["retransmissions"] > old_retrans:
            show_window(base, window_size, state)
    stats["transfer_time"] = time.monotonic() - started

    print("All packets, including END, acknowledged.")
    print("Final state:", state)
    print("Sender statistics:", stats)

    return stats


if __name__ == "__main__":
    def practice_send(packet):
        pass

    packets = list(range(8))
    base = 0
    next_seq = 0
    dup_count = 0
    window_size = 4

    state = ["-"] * len(packets)
    send_time = {}
    stats = {"transmissions": 0, "retransmissions": 0, "timeouts": 0}

    # Send packets 0, 1, 2, 3
    next_seq = fill_window(packets, base, next_seq,
                           window_size, practice_send, state, send_time, stats)
    base, dup_count = process_ack(
        base, next_seq, 1, dup_count, packets, practice_send, state, send_time, stats)

    next_seq = fill_window(packets, base, next_seq,
                           window_size, practice_send, state, send_time, stats)

    # pretend 3 more ACKs arrive, all requesting packet 1
    for _ in range(3):
        base, dup_count = process_ack(
            base, next_seq, 1, dup_count,
            packets, practice_send, state, send_time, stats
        )

    print("After duplicate ACKs:")
    print("state:", state)
    print("stats:", stats)

    # Pretend the retransmission succeeds and ACK 5 arrives.
    base, dup_count = process_ack(
        base, next_seq, 5, dup_count,
        packets, practice_send, state, send_time, stats
    )

    print("After ACK 5:")
    print("state:", state)
    print("base:", base)
    print("next_seq:", next_seq)
    print("dup_count:", dup_count)
    print("Testing timeout detection:")

    print(has_timed_out(1, 5, 10.0, 10.5, 1.0))
    print(has_timed_out(1, 5, 10.0, 11.2, 1.0))
    print(has_timed_out(5, 5, None, 11.2, 1.0))
    print("Testing actual timeout:")

    timeout = 1.0

    # Start the timer as we begin sending outstanding packets.
    timer_started = time.monotonic()

    # Send the remaining packets: 5, 6, 7.
    next_seq = fill_window(
        packets, base, next_seq, window_size,
        practice_send, state, send_time, stats
    )

    time.sleep(1.1)

    now = time.monotonic()

    if has_timed_out(base, next_seq, timer_started, now, timeout):
        print("TIMEOUT", base)
        stats["timeouts"] += 1

        retransmit(
            base, packets, practice_send, state, send_time, stats
        )

        timer_started = time.monotonic()
        dup_count = 0

    print("base:", base)
    print("next_seq:", next_seq)
    print("state:", state)
    print("stats:", stats)
