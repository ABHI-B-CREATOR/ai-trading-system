import argparse
from datetime import datetime, timezone
import json
import os
import sys
import time
import webbrowser
from getpass import getpass
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import yaml
from kiteconnect import KiteConnect

# Callback URL - configurable via environment variable
ZERODHA_CALLBACK_URL = os.environ.get("ZERODHA_CALLBACK_URL", "http://127.0.0.1:5000")


def _load_yaml(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read().strip()
        if not content:
            return None
        return yaml.safe_load(content)
    except FileNotFoundError:
        return None
    except Exception as exc:
        print(f"Failed to read {path}: {exc}")
        return None


def _write_yaml(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None
    except Exception as exc:
        print(f"Failed to read {path}: {exc}")
        return None


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def _prompt_required(label, default_value=None, secret=False):
    if default_value:
        prompt = f"{label} [{default_value}]: "
    else:
        prompt = f"{label}: "

    if secret:
        if os.name == "nt":
            value = input(f"{label} (visible): ").strip()
        else:
            try:
                value = getpass(prompt).strip()
                if not value:
                    print("(Hidden input may block paste. Please paste visibly.)")
                    value = input(f"{label} (visible): ").strip()
            except Exception:
                value = input(f"{label} (visible): ").strip()
    else:
        value = input(prompt).strip()

    if not value:
        value = default_value

    return value


def _parse_callback_url(callback_url):
    parsed = urlparse(callback_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5000
    return host, port


def _capture_request_token(callback_url, timeout_seconds=180):
    host, port = _parse_callback_url(callback_url)
    token_box = {"token": None}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            token = query.get("request_token", [None])[0]
            if token:
                token_box["token"] = token
                body = (
                    "<html><body><h3>Login captured.</h3>"
                    "<p>You can close this tab and return to the terminal.</p></body></html>"
                )
            else:
                body = (
                    "<html><body><h3>Missing request_token.</h3>"
                    "<p>Please retry the login flow.</p></body></html>"
                )
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, format, *args):
            return

    httpd = HTTPServer((host, port), CallbackHandler)
    httpd.timeout = 1

    start_time = time.time()
    while time.time() - start_time < timeout_seconds and token_box["token"] is None:
        httpd.handle_request()

    httpd.server_close()
    return token_box["token"]


def main():
    parser = argparse.ArgumentParser(description="Zerodha Access Token Generator")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Capture request_token via local callback URL"
    )
    parser.add_argument(
        "--callback",
        default=ZERODHA_CALLBACK_URL,
        help=f"Local callback URL to receive request_token (default: {ZERODHA_CALLBACK_URL})"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Seconds to wait for login redirect (default: 180)"
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(script_dir, ".."))

    config_path = os.path.join(root_dir, "8_BACKEND_APPLICATION_LAYER", "backend_settings.yaml")
    template_path = os.path.join(root_dir, "8_BACKEND_APPLICATION_LAYER", "backend_settings_zerodha.yaml")
    broker_session_path = os.path.join(root_dir, "6_EXECUTION_LAYER", "broker_auth_session.json")

    config = _load_yaml(config_path) or _load_yaml(template_path) or {}
    existing_key = config.get("zerodha_api_key")

    print("\nZerodha Access Token Generator")
    api_key = os.getenv("ZERODHA_API_KEY") or _prompt_required("Zerodha API Key", default_value=existing_key)
    if not api_key:
        print("API Key is required")
        sys.exit(1)

    api_secret = os.getenv("ZERODHA_API_SECRET") or _prompt_required("Zerodha API Secret (not stored)", secret=True)
    if not api_secret:
        print("API Secret is required")
        sys.exit(1)

    kite = KiteConnect(api_key=api_key)
    login_url = kite.login_url()
    print("\nOpen this URL and login:")
    print(login_url)

    request_token = os.getenv("ZERODHA_REQUEST_TOKEN")
    if not request_token and args.auto:
        print(f"\nWaiting for redirect on {args.callback} ...")
        try:
            webbrowser.open(login_url)
        except Exception:
            pass
        request_token = _capture_request_token(args.callback, timeout_seconds=args.timeout)

    if not request_token:
        request_token = _prompt_required("\nPaste request_token from the redirect URL")
    if not request_token:
        print("request_token is required")
        sys.exit(1)

    try:
        data = kite.generate_session(request_token, api_secret=api_secret)
    except Exception as exc:
        print(f"Failed to generate session: {exc}")
        sys.exit(1)

    access_token = data.get("access_token")
    if not access_token:
        print("No access_token received from Zerodha")
        sys.exit(1)

    generated_at = datetime.now(timezone.utc).isoformat()

    config["broker"] = "zerodha"
    config["zerodha_api_key"] = api_key
    config["zerodha_access_token"] = access_token
    config["demo_mode"] = False
    _write_yaml(config_path, config)

    broker_session = _load_json(broker_session_path) or {}
    broker_session["broker"] = "ZERODHA"
    broker_session["redirect_uri"] = args.callback
    broker_session["access_token"] = access_token
    broker_session["token_generated_time"] = generated_at
    broker_session["token_validity_hours"] = int(broker_session.get("token_validity_hours", 24) or 24)
    broker_session["paper_trading_mode"] = str(config.get("trading_mode", "paper")).lower() == "paper"
    broker_session["demo_mode"] = bool(config.get("demo_mode", False))
    _write_json(broker_session_path, broker_session)

    print("\nAccess token generated and saved")
    print(f"Updated config: {config_path}")
    print(f"Updated broker session: {broker_session_path}")
    print("Restart the backend to use the new token")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted by user.")
