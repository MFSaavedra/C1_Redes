def receive_full_message(connection_socket, buff_size=4096):
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

def parse_HTTP_message(http_message):
    """
    Parse an HTTP message into its components.
    Returns a dictionary with 'start_line', 'headers', and 'body'.
    """
    if b"\r\n\r\n" in http_message:
        header, body = http_message.split(b"\r\n\r\n", 1)
    else:
        header = http_message
        body = b""

    header_str = header.decode("utf-8", errors="replace")
    header_lines = header_str.split("\r\n")

    start_line_parts = header_lines[0].split(" ")
    if len(start_line_parts) >= 3:
        if start_line_parts[0].startswith("HTTP/"):
            start_line = {
                "version": start_line_parts[0],
                "status_code": int(start_line_parts[1]),
                "reason": " ".join(start_line_parts[2:]),
            }
        else:
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

    return {"start_line": start_line, "headers": headers, "body": body}

def create_HTTP_message(message):
    """
    Create an HTTP message from its components.
    Expects a dictionary with 'start_line', 'headers', and 'body'.
    """
    start_line = message["start_line"]
    headers = message["headers"]
    body = message["body"]

    if "method" in start_line:
        start_line_str = f"{start_line['method']} {start_line['path']} {start_line['version']}\r\n"
    else:
        start_line_str = f"{start_line['version']} {start_line['status_code']} {start_line['reason']}\r\n"
    
    headers_str = ""
    for key, value in headers.items():
        headers_str += f"{key}: {value}\r\n"

    return (start_line_str + headers_str + "\r\n").encode("utf-8") + body

def build_HTTP_response(status_code, reason, body_str, content_type="text/html; charset=utf-8"):
    """
    Build an HTTP response message.
    """
    body = body_str.encode('utf-8')
    
    response_dict = {
        "start_line": {
            "version": "HTTP/1.1",
            "status_code": status_code,
            "reason": reason
        },
        "headers": {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
            "Connection": "close"
        },
        "body": body
    }
    
    return create_HTTP_message(response_dict)
    
