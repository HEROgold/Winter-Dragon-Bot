import socket


def get_v4_port() -> int:
    """Get an available v4 port, or the port in use.

    Returns
    -------
    :class:`int`
        the port found, or in use

    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    _, v4_port = sock.getsockname()
    sock.close()

    return v4_port
