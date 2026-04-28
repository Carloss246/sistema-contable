import socket

from uvicorn import run


def _find_free_port() -> int:
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
		sock.bind(("127.0.0.1", 0))
		return sock.getsockname()[1]


def main() -> None:
	port = _find_free_port()
	print(f"Iniciando app en http://127.0.0.1:{port}")
	run("app.web:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
	main()
