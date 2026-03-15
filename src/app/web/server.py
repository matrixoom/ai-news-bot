"""Development web server for the initial dashboard shell."""
from wsgiref.simple_server import make_server

from .app import create_web_app



def run_dev_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the minimal dashboard shell."""
    app = create_web_app()
    with make_server(host, port, app) as server:
        print(f"Serving dashboard on http://{host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    run_dev_server()
