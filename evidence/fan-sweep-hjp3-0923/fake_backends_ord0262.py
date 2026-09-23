"""Two fake backends for the disconnected half of the fan sweep (my own ports only).

  :8599  SILENT  - accepts the TCP connection and never answers (the "no answer" third state)
  :8598  FIFTY   - answers every /api/ call with a bare 500 (the "server said no" state)

Neither touches the product, the tunnel, :4781/:4782 or a user DB. Started by the fan sweep;
kill by PID printed here.
"""
import socket
import threading

SILENT = 8599
FIFTY = 8598


def serve_silent():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('127.0.0.1', SILENT))
    s.listen(64)
    held = []
    while True:
        c, _ = s.accept()
        held.append(c)  # accept, read nothing, never respond


def serve_fifty():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('127.0.0.1', FIFTY))
    s.listen(64)
    body = b'Internal Server Error'
    while True:
        c, _ = s.accept()
        try:
            c.settimeout(3)
            try:
                c.recv(65536)
            except Exception:
                pass
            head = (b'HTTP/1.1 500 Internal Server Error\r\n'
                    b'content-type: text/plain; charset=utf-8\r\n'
                    b'content-length: %d\r\nconnection: close\r\n\r\n' % len(body))
            c.sendall(head + body)
        finally:
            c.close()


threads = [threading.Thread(target=serve_silent, daemon=True),
           threading.Thread(target=serve_fifty, daemon=True)]
for t in threads:
    t.start()
print('fake backends up: silent=%d fifty=%d' % (SILENT, FIFTY), flush=True)
threading.Event().wait()
