import socket
import argparse
import asyncio
from aioquic.asyncio import serve
from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.events import StreamDataReceived, HandshakeCompleted, ConnectionTerminated

DATA_SIZE_MB = {"500MB": 500 * 1024 * 1024, "1GB": 1024 * 1024 * 1024}

# TCP Server


def tcp_server(host, port, stop_and_wait=True):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(1)
    print(f"TCP Server listening on {host}:{port}...")

    conn, addr = sock.accept() #accept conexiunea
    print(f"Connected by {addr}")

    total_received = 0

    try:
        while True:
            data = conn.recv(65535)  # Citim cât mai mult posibil
            if not data: #daca nu sunt date inchid connexiunea
                break

            total_received += len(data)

            if stop_and_wait:
                conn.sendall(b"A")  # Trimite ACK doar pt Stop-and-Wait

        print("Transfer completed successfully.")
    except ConnectionResetError:
        print("Connection reset.")
    finally:
        conn.close()
        print(f"TCP Server: Received {total_received} bytes")



# UDP Server
def udp_server(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Creăm un socket UDP
    sock.bind((host, port)) # Legăm socket-ul la o adresă și port
    total_received = 0
    received_messages = 0
    sent_messages = 0

    print(f"UDP Server listening on {host}:{port}...")

    try:
        while True:
            data, addr = sock.recvfrom(65535) # primeste date de la client

            if data == b"FINISHED":
                print("\nUDP Server: Transfer complet! Aștept numărul de mesaje trimise...")
                # După "FINISHED", mai așteptăm încă un mesaj (cu numărul de mesaje trimise)
                data, addr = sock.recvfrom(65535)  # Primim numărul de mesaje trimise
                if data.startswith(b"Sent messages:"):
                    sent_messages = int(data.decode().split(":")[1].strip())
                    print(f"UDP Server: Client a trimis {sent_messages} mesaje.")
                break

            total_received += len(data)
            received_messages += 1
            sock.sendto(b"A", addr)  # Trimite ACK

    except KeyboardInterrupt:
        print("\nUDP Server: Oprit manual.")

    finally:
        print(f"\nUDP Server: Received {received_messages} messages, {total_received} bytes")

        if sent_messages > 0:
            loss_rate = (sent_messages - received_messages) / sent_messages * 100
            print(f"UDP Data Loss: {loss_rate:.2f}%")
        else:
            print("UDP Data Loss: N/A (Sent messages not received)")

        sock.close()


# QUIC Server

class MyQuicServerProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_received = 0
        self.total_messages = 0

    def quic_event_received(self, event):
        if isinstance(event, HandshakeCompleted):
            print("Handshake completed")
        elif isinstance(event, StreamDataReceived):
            self.total_received += len(event.data)
            self.total_messages += 1
            print(f"Received {len(event.data)} bytes, total received: {self.total_received} bytes, total messages: {self.total_messages}")

            # Trimite un mesaj de confirmare înapoi
            self._quic.send_stream_data(event.stream_id, b"A", end_stream=False)  # trimite un ACK
        elif isinstance(event, ConnectionTerminated):
            print("Connection terminated")

    def connection_lost(self, exc):
        super().connection_lost(exc)
        print(f"QUIC Server: Received {self.total_messages} messages, {self.total_received} bytes")
        print("Protocol used: QUIC")


async def quic_server(host, port):
    configuration = QuicConfiguration(is_client=False)
    configuration.load_cert_chain(certfile='server.crt', keyfile='server.key')

    server = await serve(
        host=host, port=port,
        configuration=configuration,
        create_protocol=MyQuicServerProtocol
    )
    print(f"QUIC server running on {host}:{port}")

    await asyncio.Event().wait()



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", choices=["tcp", "udp", "quic"], required=True)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    if args.protocol == "tcp":
        tcp_server(args.host, args.port)
    elif args.protocol == "udp":
        udp_server(args.host, args.port)
    elif args.protocol == "quic":
        asyncio.run(quic_server(args.host, args.port))



#python servers.py --protocol tcp --host 127.0.0.1 --port 5001

#python servers.py --protocol udp --host 127.0.0.1 --port 5001

#python servers.py --protocol quic --host 127.0.0.1 --port 5002
