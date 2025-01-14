import socket


v4_port = 5000

def get_v4_port() -> int:
    """Get a random available v4 port, or the port in use.

    Returns
    -------
    :class:`int`
        the port found, or in use

    """
    # FIXME @<HEROgold>: A randomized port doesn't work with oath2 requests, as discord requires a static port.
    # 130
    # This is why the v4_port is set to 5000 manually.
    global v4_port
    if v4_port != 0:
        return v4_port

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    _, v4_port = sock.getsockname()
    sock.close()

    return v4_port
