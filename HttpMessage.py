"""HTTP wire format over raw sockets: receive, parse and serialize messages."""


class HttpMessage:
    """An HTTP message, request or response, in its parsed form."""

    def __init__(self, start_line, headers=None, body=b"", raw=None):
        """
        start_line is {"method", "path", "version"} for a request and
        {"version", "status_code", "reason"} for a response. body stays bytes
        (not necessarily text); raw holds the message as received, or None if
        it was built in memory.
        """
        self.start_line = start_line
        self.headers = headers if headers is not None else {}
        self.body = body
        # los bytes tal como llegaron; None si el mensaje fue construido
        self.raw = raw

    @staticmethod
    def _read_raw(connection_socket, buff_size=4096):
        """
        Read one complete message off a socket, in two phases: recv until
        "\\r\\n\\r\\n" appears, then until the body reaches Content-Length.
        This is what allows a buffer smaller than the message.

        A message without Content-Length is assumed to have no body, so
        chunked or close-delimited responses get truncated.
        """
        full_message = b""

        while b"\r\n\r\n" not in full_message:
            chunk = connection_socket.recv(buff_size)
            if not chunk:
                break
            full_message += chunk

        if not full_message:
            return b""

        header, body = full_message.split(b"\r\n\r\n", 1)

        content_length = 0
        for line in header.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                content_length = int(line.split(b":")[1].strip())
                break

        while len(body) < content_length:
            chunk = connection_socket.recv(buff_size)
            if not chunk:
                break
            body += chunk

        return header + b"\r\n\r\n" + body

    @classmethod
    def receive(cls, connection_socket, buff_size=4096):
        """Read and parse a message; None if the peer sent nothing."""
        raw = cls._read_raw(connection_socket, buff_size)
        if not raw:
            return None
        return cls.parse(raw)

    @staticmethod
    def _parse_start_line(line):
        """
        Parse the first line. A request line ends with the HTTP version
        ("GET /path HTTP/1.1"), a status line begins with it, so a leading
        "HTTP/" gives the direction. Raises ValueError if it is neither.
        """
        if line.startswith("HTTP/"):
            # la reason phrase puede llevar espacios ("Internal Server Error")
            # o venir vacía, así que solo separamos los dos primeros campos
            parts = line.split(" ", 2)
            if len(parts) < 2 or not parts[1].isdigit():
                raise ValueError(f"status line HTTP mal formada: {line!r}")
            return {
                "version": parts[0],
                "status_code": int(parts[1]),
                "reason": parts[2] if len(parts) == 3 else "",
            }

        # una request line tiene exactamente 3 campos
        parts = line.split(" ")
        if len(parts) != 3:
            raise ValueError(f"request line HTTP mal formada: {line!r}")
        return {"method": parts[0], "path": parts[1], "version": parts[2]}

    @classmethod
    def parse(cls, http_message):
        """
        Split a message into start line, headers and body, keeping the
        original bytes in raw. Only the headers are decoded.
        """
        if b"\r\n\r\n" in http_message:
            header, body = http_message.split(b"\r\n\r\n", 1)
        else:
            header = http_message
            body = b""

        header_str = header.decode("utf-8")
        header_lines = header_str.split("\r\n")

        start_line = cls._parse_start_line(header_lines[0])

        headers = {}
        for line in header_lines[1:]:
            if ": " in line:
                key, value = line.split(": ", 1)
                headers[key] = value

        return cls(start_line, headers, body, raw=http_message)

    @classmethod
    def response(cls, status_code, reason, body,
                 content_type="text/html; charset=utf-8", extra_headers=None):
        """
        Build a response from scratch. A str body is encoded first, so that
        Content-Length counts bytes and not characters.
        """
        if isinstance(body, str):
            body = body.encode('utf-8')

        headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
            "Connection": "close"
        }
        if extra_headers:
            headers.update(extra_headers)

        start_line = {
            "version": "HTTP/1.1",
            "status_code": status_code,
            "reason": reason
        }

        return cls(start_line, headers, body)

    def to_bytes(self):
        """
        Serialize back to bytes. Content-Length is recomputed, but only if the
        message already had it, so an edited body keeps a truthful length.
        """
        start_line = self.start_line
        if "method" in start_line:
            first_line = f"{start_line['method']} {start_line['path']} {start_line['version']}"
        else:
            first_line = f"{start_line['version']} {start_line['status_code']} {start_line['reason']}"

        body = self.body.encode('utf-8') if isinstance(self.body, str) else self.body

        # si el mensaje declara Content-Length, lo recalculamos por si el body cambió
        headers = dict(self.headers)
        for key in headers:
            if key.lower() == "content-length":
                headers[key] = str(len(body))
                break

        lines = [first_line] + [f"{key}: {value}" for key, value in headers.items()]

        return ("\r\n".join(lines) + "\r\n\r\n").encode('utf-8') + body


def parse_HTTP_message(http_message: bytes) -> HttpMessage:
    """Bytes to structure. The name the assignment asks for."""
    return HttpMessage.parse(http_message)


def create_HTTP_message(message: HttpMessage) -> bytes:
    """Structure back to bytes. The inverse of parse_HTTP_message."""
    return message.to_bytes()
