"""A dumb TCP relay so one port can be made to answer, or stop answering, without restarting anything.

Why this exists: the trial's Agent leg is configured to a single URL, and the backend's traveller-auth secret is
regenerated on every boot -- so restarting a stack to change the model endpoint would also throw away the
traveller's session and the Journey under test.  Relaying 127.0.0.1:59999 -> 127.0.0.1:7863 lets the SAME tab,
SAME journey and SAME task go from "nothing is listening" (a real transport failure the product must survive) to
"a real gateway answers" between two presses of the same button.

It does not invent any answer: bytes are forwarded verbatim in both directions, and no response is cached or
synthesised.  Nothing is printed except counts -- no headers, no bodies, no keys.
"""
import socket
import sys
import threading
import time

LISTEN = ("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 59999)
UPSTREAM = ("127.0.0.1", int(sys.argv[2]) if len(sys.argv) > 2 else 7863)
stats = {"connections": 0, "bytes_to_upstream": 0, "bytes_to_client": 0, "errors": 0}


def pump(source, target, key):
    try:
        while True:
            chunk = source.recv(65536)
            if not chunk:
                break
            stats[key] += len(chunk)
            target.sendall(chunk)
    except OSError:
        stats["errors"] += 1
    finally:
        for handle in (source, target):
            try:
                handle.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            handle.close()


def serve():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(LISTEN)
    listener.listen(16)
    print("relay %s:%d -> %s:%d" % (LISTEN[0], LISTEN[1], UPSTREAM[0], UPSTREAM[1]), flush=True)
    last = time.time()
    while True:
        client, _peer = listener.accept()
        stats["connections"] += 1
        try:
            upstream = socket.create_connection(UPSTREAM, timeout=300)
        except OSError:
            stats["errors"] += 1
            client.close()
            continue
        threading.Thread(target=pump, args=(client, upstream, "bytes_to_upstream"), daemon=True).start()
        threading.Thread(target=pump, args=(upstream, client, "bytes_to_client"), daemon=True).start()
        if time.time() - last > 20:
            last = time.time()
            print("stats %s" % stats, flush=True)


if __name__ == "__main__":
    serve()
