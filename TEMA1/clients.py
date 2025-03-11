import socket
import time
import argparse
import asyncio
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration

DATA_SIZE_MB = {"500MB": 500 * 1024 * 1024, "1GB": 1024 * 1024 * 1024}

# TCP Client
def tcp_client(host, port, data_size, msg_size, streaming=True):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Creăm un socket TCP
    sock.connect((host, port)) # Conectăm la server

    data = b"X" * msg_size # Mesajul de trimis
    total_sent = 0
    sent_messages = 0
    start_time = time.time()

    while total_sent < data_size:
        sock.sendall(data) # Trimitem mesajul
        if not streaming:  # Dacă Stop-and-Wait, așteptăm ACK
            ack = sock.recv(1) # Așteptăm ACK
            if ack != b"A":
                print("ACK error!")
                break
        total_sent += msg_size
        sent_messages += 1

    sock.close()
    end_time = time.time()
    print(f"TCP: Sent {total_sent} bytes in {end_time - start_time:.2f} seconds, Total messages: {sent_messages}")

# UDP Client
def udp_client(host, port, data_size, msg_size, stop_and_wait=True):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Creăm un socket UDP
    data = b"A" * msg_size
    total_sent = 0
    sent_messages = 0
    start_time = time.time()

    while total_sent < data_size:
        sock.sendto(data, (host, port)) # Trimitem mesajul
        if stop_and_wait:
            sock.recvfrom(1)  # Așteaptă ACK (Stop-and-Wait)
        total_sent += msg_size
        sent_messages += 1

    # Trimitem mesajul de închidere și numărul total de mesaje
    sock.sendto(b"FINISHED", (host, port))
    sock.sendto(f"Sent messages: {sent_messages}".encode(), (host, port))

    elapsed_time = time.time() - start_time
    print(f"UDP: Sent {total_sent} bytes in {elapsed_time:.2f} seconds, Total messages: {sent_messages}")
    sock.close()


# QUIC Client
# QUIC Client
async def quic_client(host, port, data_size, msg_size, stop_and_wait=True):
    configuration = QuicConfiguration(is_client=True)
    configuration.load_cert_chain(certfile='client.crt', keyfile='client.key')
    configuration.verify_mode = False  # Disable certificate verification

    async with connect(host, port, configuration=configuration) as protocol:
        stream_id = protocol._quic.get_next_available_stream_id()
        data = b"X" * msg_size
        total_sent = 0
        sent_messages = 0  # Variabilă pentru numărul de mesaje trimise
        start_time = time.time()

        while total_sent < data_size:
            protocol._quic.send_stream_data(stream_id, data)
            if stop_and_wait:
                await asyncio.sleep(0.01)  # simulate stop-and-wait behavior
            total_sent += msg_size
            sent_messages += 1  # Incrementăm numărul de mesaje trimise
            print(f"QUIC: Sent {total_sent} bytes so far...")

        end_time = time.time()
        print(f"QUIC: Sent {total_sent} bytes in {end_time - start_time:.2f} seconds, Total messages: {sent_messages}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", choices=["tcp", "udp", "quic"], required=True)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--data_size", choices=["500MB", "1GB"], default="500MB")
    parser.add_argument("--msg_size", type=int, default=1024)
    parser.add_argument("--streaming", action="store_true")
    args = parser.parse_args()

    if args.protocol == "tcp":
        tcp_client(args.host, args.port, DATA_SIZE_MB[args.data_size], args.msg_size, args.streaming)
    elif args.protocol == "udp":
        udp_client(args.host, args.port, DATA_SIZE_MB[args.data_size], args.msg_size, not args.streaming)

    elif args.protocol == "quic":
        asyncio.run(
            quic_client(args.host, args.port, DATA_SIZE_MB[args.data_size], args.msg_size, not args.streaming)
        )


#python clients.py --protocol tcp --host 127.0.0.1 --port 5001 --data_size 1GB --msg_size 4096 --streaming

#python clients.py --protocol udp --host 127.0.0.1 --port 5001 --data_size 1GB --msg_size 16384

# python clients.py --protocol quic --host 127.0.0.1 --port 5002 --data_size 1GB --msg_size 65535
