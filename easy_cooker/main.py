"""Run from this directory: python3 main.py --chefs 2 --tables 8."""
import argparse
from app.api import make_server
from app.service import RestaurantService


def main():
    parser = argparse.ArgumentParser(description="easy_cooker development server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--chefs", type=int, default=2)
    parser.add_argument("--tables", type=int, default=8)
    parser.add_argument("--first-course-seconds", type=int, default=900)
    args = parser.parse_args()
    service = RestaurantService(args.chefs, args.tables, args.first_course_seconds)
    server = make_server(service, args.host, args.port)
    print(f"easy_cooker listening on http://{args.host}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
