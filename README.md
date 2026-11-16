# EECE 350 Final Project

## Reliable File Transfer over UDP

A file is sent over UDP (which can lose, repeat and reorder packets) and arrives complete and correct.
Python 3, standard library only.

## Files

| File | What it does |
|---|---|
| `protocol.py` | The packet format all members agreed on |
| `packets.py` | Reads and splits the file, constructs packets and creates END with its hash |
| `channel.py` | Unreliable channel: drops and reorders packets on purpose |
| `sender_window.py` | Sending window, ACK handling, retransmissions, adaptive timeout and live display |
| `sender.py` | Launcher connecting packet creation, the UDP socket, the channel and the window controller |
| `receiver.py` | Receiver: cumulative ACKs, buffering, reassembly, SHA-256 check |
| `test_input.txt` | Example file the sender transfers |
| `practice/` | Practice and test scripts used while building the receiver |

## Packet format

```
type (1 byte) | seq (4 bytes) | length (2 bytes) | data
```

| Type | seq | data |
|---|---|---|
| DATA (0) | chunk number | a piece of the file |
| ACK (1) | next packet expected | nothing |
| END (2) | number of chunks | SHA-256 of the whole file (32 bytes) |

## How to run

Start the receiver first, then the sender:

```
python receiver.py                  # listens on port 9000, writes received.txt
python receiver.py 9000 out.bin     # choose the port and output file

```

The receiver prints its settings, one line per packet (for example `RECV 12 in order -> ACK 13`),
and a summary ending in `SHA-256 : MATCH` or `MISMATCH`.
In a second terminal, run the sender:

```powershell
python sender.py
```

The input file is selected using `filepath` in `sender.py`. The current example uses `test_input.txt`.

## Settings

The sender settings are edited in `sender.py`.

| Setting | Meaning |
|---|---|
| `filepath` | Path of the file to transfer. |
| `window_size` | Maximum sending-window span. It must be a positive integer. |
| Second argument of `split_file` | Number of file bytes per DATA packet. Our small demo uses 8. |
| `destination` | Receiver IP address and port. Our local tests use `("127.0.0.1", 9000)`. |
| `loss` | Simulated packet-drop probability, between 0 and 1. |
| `reorder` | Probability of holding a packet when no packet is already held, between 0 and 1. |
| `random.seed(...)` | Makes the simulator's random choices repeatable. |

The simulator requires `loss + reorder <= 1`. The receiver's listening port must match the sender's destination port. For two computers, replace `127.0.0.1` with the receiver's reachable IPv4 address.

The initial retransmission timeout is 1 second. It is updated using RTT measurements, with a minimum of 1 second. The socket's 0.05-second receive wait lets the controller check for ACKs and timer expiration regularly; it is a separate setting from the retransmission timeout.

## How it works

Jean Paul's packet functions split the file into chunks and add a seven-byte header using `struct` format `!BIH`: packet type, sequence number and payload length.

| Packet | Type | Contents |
|---|---:|---|
| DATA | 0 | A numbered file chunk. Numbering starts at 0. |
| ACK | 1 | The next expected sequence number, with no payload. |
| END | 2 | The number of DATA chunks and the original file's SHA-256 hash. |

ACK `k` confirms all packets before `k`. For five DATA packets numbered 0 to 4, END is packet 5 and ACK 6 confirms completion.

The sender fills its window and advances it when new cumulative ACKs arrive. Three duplicate ACKs trigger fast retransmit. A timeout retransmits the oldest unacknowledged packet and doubles the waiting limit. RTT estimates exclude ACKs covering retransmitted packets to avoid ambiguous measurements.

Every original transmission and retransmission passes through the unreliable channel. A held packet is released after handling the next sending attempt. The launcher flushes any trailing held packet when END is attempted and performs final channel cleanup after completion.

The receiver buffers packets arriving early and accepts them when the missing packet fills the gap. It reconstructs the file and checks its hash.

The display shows packet events, the active window and nearby packet states: `-` for unsent, `S` for sent, `A` for acknowledged and `R` for retransmitted. Final summaries show sending attempts, retransmissions, timeouts, duration, actual UDP sends, drops, reordering selections and the file hash result.

## Contributions

- **Jean Paul Chaaya:** file splitting, packet construction and validation, END hash generation, the unreliable channel and its statistics. He also merged the initial sender-window branch.
- **Andrew Samaha:** receiver, cumulative ACKs, buffering, duplicate handling, file reconstruction and hash verification. He also worked on the initial repository documentation and protocol description.
- **Jinan Sief El Deen:** sending window, ACK processing, fast retransmit, timeout handling, RTT estimation, backoff, packet states, live window display, sender integration and documentation updates.

## Testing

The following settings produce useful demonstrations with five DATA chunks plus END and a window size of 4:

| Loss | Reorder | Seed | Expected demonstration |
|---:|---:|---:|---|
| 0.0 | 0.0 | 7 | Normal transfer without retransmissions. |
| 0.1 | 0.2 | 7 | Reordering and timeout recovery after packet 3 is dropped twice. |
| 0.1 | 0.2 | 37 | Three duplicate ACKs and fast retransmit after packet 1 is dropped. |
| 0.1 | 0.2 | 144 | Timeout recovery after the first END attempt is dropped. |

Start a fresh receiver for each run and check for `MATCH`. Changing the file size or settings can change the event sequence. Sender transmission attempts include simulated drops, whereas the channel's UDP-send counter counts actual sends.

## AI assistance and sources
Jinan used ai only as a learning tool to understand syntax + work through explanaitons. (Also used AI to format and refine the draft of README)

Andrew used Ai to look up library functions and syntax.
