class HttpMessage:
    """
    An HTTP message (request or response) in its parsed form.

    Encapsulates the wire format: receiving from a socket, parsing bytes into
    its components, and serializing back to bytes.
    """

    def __init__(self, start_line, headers=None, body=b"", raw=None):
        self.start_line = start_line
        self.headers = headers if headers is not None else {}
        self.body = body
        # los bytes tal como llegaron; None si el mensaje fue construido
        self.raw = raw

    @staticmethod
    def _read_raw(connection_socket, buff_size=4096):
        """
        Receive a full HTTP message from the connection socket.
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
        """
        Read a full HTTP message from the socket and parse it.
        Returns None if the connection did not deliver anything.
        """
        raw = cls._read_raw(connection_socket, buff_size)
        if not raw:
            return None
        return cls.parse(raw)

    @classmethod
    def parse(cls, http_message):
        """
        Parse an HTTP message into its components.
        Returns an HttpMessage with 'start_line', 'headers' and 'body'.
        """
        if b"\r\n\r\n" in http_message:
            header, body = http_message.split(b"\r\n\r\n", 1)
        else:
            header = http_message
            body = b""

        header_str = header.decode("utf-8")
        header_lines = header_str.split("\r\n")

        start_line_parts = header_lines[0].split(" ")
        if len(start_line_parts) == 3:
            start_line = {
                "method": start_line_parts[0],
                "path": start_line_parts[1],
                "version": start_line_parts[2],
            }

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
        Build an HTTP response message.
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
        Convert this message back into an HTTP message (in bytes).
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
