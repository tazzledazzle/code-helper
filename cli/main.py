"""CLI entry point: run-tests and chat subcommands."""

import argparse
import os
import sys

import httpx


def _api_base_url() -> str:
    return os.environ.get("CODE_HELPER_API_URL", "http://localhost:8000").rstrip("/")


def _run_tests(path: str) -> int:
    project_path = os.path.abspath(path)
    base_url = _api_base_url()
    payload = {"project_path": project_path, "action": "run_tests"}
    try:
        with httpx.Client(base_url=base_url, timeout=120.0) as client:
            response = client.post("/run", json=payload)
            response.raise_for_status()
    except httpx.ConnectError as e:
        print(f"Error: cannot connect to {base_url}", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1
    except httpx.HTTPStatusError as e:
        print(f"Error: {e.response.status_code} {e.response.text}", file=sys.stderr)
        return 1

    data = response.json()
    summary = data.get("summary", "")
    stdout = data.get("stdout", "")
    stderr = data.get("stderr", "")
    exit_code = data.get("exit_code", 1)

    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    if summary and summary != (stdout.strip() or "Tests passed"):
        print(summary)
    return exit_code


def _chat_one(message: str, project_path: str | None) -> None:
    base_url = _api_base_url()
    payload = {"message": message}
    if project_path:
        payload["project_path"] = os.path.abspath(project_path)
    try:
        with httpx.Client(base_url=base_url, timeout=300.0) as client:
            response = client.post("/chat", json=payload)
            response.raise_for_status()
    except httpx.ConnectError as e:
        print(f"Error: cannot connect to {base_url}", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return
    except httpx.HTTPStatusError as e:
        print(f"Error: {e.response.status_code} {e.response.text}", file=sys.stderr)
        return

    data = response.json()
    text = data.get("response", "")
    print(text)


def _chat_interactive(project_path: str | None) -> None:
    print("Chat with code-helper (empty line or Ctrl+C to quit)")
    try:
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
            if not line:
                break
            _chat_one(line, project_path)
    except KeyboardInterrupt:
        print()
        pass


def main() -> None:
    parser = argparse.ArgumentParser(prog="code-helper", description="Code helper CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run-tests", help="Run tests via Crew API")
    run_parser.add_argument(
        "--path",
        default=os.getcwd(),
        help="Project path (default: current directory)",
    )

    chat_parser = subparsers.add_parser("chat", help="Chat with crew (interactive or one message)")
    chat_parser.add_argument("--path", default=None, help="Project path (optional)")
    chat_parser.add_argument("--message", "-m", default=None, help="Single message (one shot); omit for interactive")

    args = parser.parse_args()

    if args.command == "run-tests":
        exit_code = _run_tests(args.path)
        sys.exit(exit_code)
    elif args.command == "chat":
        if args.message is not None:
            _chat_one(args.message, args.path)
        else:
            _chat_interactive(args.path)


if __name__ == "__main__":
    main()
