#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
from urllib import request as urlrequest
from urllib import parse as urlparse
from urllib.error import HTTPError, URLError
import ssl

LOCK = threading.Lock()


def parse_key_value_pairs(pairs: Optional[List[str]], sep: str = "=") -> Dict[str, str]:
    result: Dict[str, str] = {}
    if not pairs:
        return result
    for item in pairs:
        if item is None:
            continue
        if sep not in item:
            raise ValueError(f"Invalid pair '{item}'. Expected format key{sep}value")
        key, value = item.split(sep, 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Invalid pair '{item}'. Key is empty")
        result[key] = value
    return result


def parse_header_pairs(pairs: Optional[List[str]]) -> Dict[str, str]:
    if not pairs:
        return {}
    headers: Dict[str, str] = {}
    for item in pairs:
        if ":" not in item:
            raise ValueError(f"Invalid header '{item}'. Expected format 'Name: Value'")
        name, value = item.split(":", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            raise ValueError(f"Invalid header '{item}'. Name is empty")
        headers[name] = value
    return headers


def load_json_from_file(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_body(args: argparse.Namespace) -> Tuple[Optional[bytes], Optional[bytes]]:
    data_bytes: Optional[bytes] = None
    json_bytes: Optional[bytes] = None

    if args.json is not None and args.data is not None:
        raise ValueError("Provide either --json or --data, not both")

    if args.json is not None:
        if os.path.isfile(args.json):
            obj = load_json_from_file(args.json)
        else:
            try:
                obj = json.loads(args.json)
            except json.JSONDecodeError as exc:
                raise ValueError(f"--json is not valid JSON: {exc}")
        json_bytes = json.dumps(obj, ensure_ascii=False).encode("utf-8")

    if args.data is not None:
        if os.path.isfile(args.data):
            with open(args.data, "rb") as f:
                data_bytes = f.read()
        else:
            data_bytes = args.data.encode("utf-8")

    return data_bytes, json_bytes


def build_proxies(args: argparse.Namespace) -> Optional[Dict[str, str]]:
    if not args.proxy:
        return None
    return {
        "http": args.proxy,
        "https": args.proxy,
    }


def merge_cookies_into_header(headers: Dict[str, str], cookies: Dict[str, str]) -> None:
    if not cookies:
        return
    existing = headers.get("Cookie", "").strip()
    jar = "; ".join([f"{k}={v}" for k, v in cookies.items()])
    headers["Cookie"] = f"{existing}; {jar}".strip("; ").strip()


class NoRedirect(urlrequest.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401, N802
        return None


def attach_params_to_url(url: str, params: Dict[str, str]) -> str:
    if not params:
        return url
    parts = urlparse.urlsplit(url)
    current_query = dict(urlparse.parse_qsl(parts.query, keep_blank_values=True))
    current_query.update(params)
    new_query = urlparse.urlencode(current_query, doseq=True)
    new_parts = urlparse.SplitResult(parts.scheme, parts.netloc, parts.path, new_query, parts.fragment)
    return urlparse.urlunsplit(new_parts)


def build_opener(verify_tls: bool, proxies: Optional[Dict[str, str]], follow_redirects: bool):
    handlers = []

    if proxies:
        handlers.append(urlrequest.ProxyHandler(proxies))

    context = None
    if not verify_tls:
        context = ssl._create_unverified_context()  # noqa: S501
    else:
        context = ssl.create_default_context()

    handlers.append(urlrequest.HTTPSHandler(context=context))

    if not follow_redirects:
        handlers.append(NoRedirect())

    opener = urlrequest.build_opener(*handlers)
    return opener


def build_and_send_request(
    url: str,
    method: str,
    params: Dict[str, str],
    headers: Dict[str, str],
    cookies: Dict[str, str],
    timeout: float,
    allow_redirects: bool,
    verify_tls: bool,
    proxies: Optional[Dict[str, str]],
    data_bytes: Optional[bytes],
    json_bytes: Optional[bytes],
) -> Tuple[int, Dict[str, str], bytes, float]:
    final_url = attach_params_to_url(url, params)

    final_headers = dict(headers) if headers else {}
    merge_cookies_into_header(final_headers, cookies)

    body: Optional[bytes] = None
    if json_bytes is not None:
        body = json_bytes
        if "Content-Type" not in {k.title(): v for k, v in final_headers.items()}:
            final_headers["Content-Type"] = "application/json; charset=utf-8"
    elif data_bytes is not None:
        body = data_bytes

    req = urlrequest.Request(final_url, data=body, method=method)
    for k, v in final_headers.items():
        req.add_header(k, v)

    opener = build_opener(verify_tls=verify_tls, proxies=proxies, follow_redirects=allow_redirects)

    start = time.perf_counter()
    try:
        with opener.open(req, timeout=timeout) as resp:
            content = resp.read()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            status = getattr(resp, "status", resp.getcode())
            headers_dict = {k: v for k, v in resp.headers.items()}
            return status, headers_dict, content, elapsed_ms
    except HTTPError as e:
        # Treat HTTPError as a response (e.g., when redirects are disabled)
        try:
            content = e.read()
        except Exception:
            content = b""
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        status = e.code
        headers_dict = {k: v for k, v in e.headers.items()} if e.headers else {}
        return status, headers_dict, content, elapsed_ms
    except URLError as e:
        raise RuntimeError(str(e))


def safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in value)[:128]


def perform_request_with_retries(
    name: str,
    url: str,
    method: str,
    params: Dict[str, str],
    base_headers: Dict[str, str],
    base_cookies: Dict[str, str],
    session_value: Optional[str],
    session_header_name: Optional[str],
    session_cookie_name: Optional[str],
    timeout: float,
    allow_redirects: bool,
    verify_tls: bool,
    proxies: Optional[Dict[str, str]],
    data_bytes: Optional[bytes],
    json_bytes: Optional[bytes],
    retries: int,
    backoff_base_ms: int,
    delay_between_ms: int,
    save_dir: Optional[str],
    save_body: bool,
) -> Dict:
    headers = dict(base_headers) if base_headers else {}
    cookies = dict(base_cookies) if base_cookies else {}

    if session_value:
        if session_header_name:
            headers[session_header_name] = session_value
        if session_cookie_name:
            cookies[session_cookie_name] = session_value

    attempt = 0
    last_exc: Optional[Exception] = None
    while attempt <= retries:
        try:
            if attempt > 0 and backoff_base_ms > 0:
                sleep_ms = backoff_base_ms * (2 ** (attempt - 1))
                time.sleep(sleep_ms / 1000.0)

            if delay_between_ms > 0:
                time.sleep(delay_between_ms / 1000.0)

            status, headers_dict, content, elapsed_ms = build_and_send_request(
                url=url,
                method=method,
                params=params,
                headers=headers,
                cookies=cookies,
                timeout=timeout,
                allow_redirects=allow_redirects,
                verify_tls=verify_tls,
                proxies=proxies,
                data_bytes=data_bytes,
                json_bytes=json_bytes,
            )

            record: Dict = {
                "name": name,
                "status": status,
                "elapsed_ms": round(elapsed_ms, 2),
                "response_headers": headers_dict,
            }

            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
                file_base = safe_filename(name)
                meta_path = os.path.join(save_dir, f"{file_base}.meta.json")
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(record, f, ensure_ascii=False, indent=2)
                if save_body:
                    body_path = os.path.join(save_dir, f"{file_base}.body")
                    with open(body_path, "wb") as f:
                        f.write(content)

            return record
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            attempt += 1

    message = str(last_exc) if last_exc else "Unknown error"
    return {
        "name": name,
        "error": message,
    }


def run_concurrent_requests(args: argparse.Namespace) -> List[Dict]:
    base_params = parse_key_value_pairs(args.param or [], sep="=")
    base_cookies = parse_key_value_pairs(args.cookie or [], sep="=")
    base_headers = parse_header_pairs(args.header or [])
    data_bytes, json_bytes = parse_body(args)
    proxies = build_proxies(args)

    names_and_sessions: List[Tuple[str, Optional[str]]] = []

    if args.session_file:
        if not os.path.isfile(args.session_file):
            raise FileNotFoundError(f"Session file not found: {args.session_file}")
        with open(args.session_file, "r", encoding="utf-8") as f:
            for line in f:
                token = line.strip()
                if not token:
                    continue
                names_and_sessions.append((token, token))
    else:
        names_and_sessions.append((args.name or "request", None))

    results: List[Dict] = []

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        future_to_name = {}
        for name, session_value in names_and_sessions:
            future = executor.submit(
                perform_request_with_retries,
                name=name,
                url=args.url,
                method=args.method,
                params=base_params,
                base_headers=base_headers,
                base_cookies=base_cookies,
                session_value=session_value,
                session_header_name=args.session_header_name,
                session_cookie_name=args.session_cookie_name,
                timeout=args.timeout,
                allow_redirects=args.follow_redirects,
                verify_tls=not args.no_verify,
                proxies=proxies,
                data_bytes=data_bytes,
                json_bytes=json_bytes,
                retries=args.retries,
                backoff_base_ms=args.backoff_ms,
                delay_between_ms=args.delay_ms,
                save_dir=args.save_dir,
                save_body=args.save_body,
            )
            future_to_name[future] = name

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                result = {"name": name, "error": str(exc)}
            results.append(result)
            with LOCK:
                if "error" in result:
                    print(f"[!] {name}: ERROR -> {result['error']}")
                else:
                    print(f"[+] {name}: {result['status']} in {result['elapsed_ms']}ms")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            for item in results:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    return results


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Safe stdlib HTTP runner CLI: concurrent requests with full control over "
            "headers, cookies, params, method, retries, proxies, TLS, and output."
        )
    )
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--method", default="GET", choices=[
        "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"
    ], help="HTTP method")

    parser.add_argument("--param", action="append", help="Query param as key=value (repeatable)")
    parser.add_argument("--cookie", action="append", help="Cookie as key=value (repeatable)")
    parser.add_argument("--header", action="append", help="Header as 'Name: Value' (repeatable)")

    parser.add_argument("--session-file", help="Path to file with one token per line (optional)")
    parser.add_argument("--session-header-name", help="Header name to carry the session token (optional)")
    parser.add_argument("--session-cookie-name", help="Cookie name to carry the session token (optional)")
    parser.add_argument("--name", help="Name for single-request mode (used when no session file)")

    parser.add_argument("--json", help="Inline JSON or path to JSON file for request body")
    parser.add_argument("--data", help="Raw data string or path to file for request body")

    parser.add_argument("--timeout", type=float, default=30.0, help="Request timeout seconds (default: 30)")
    parser.add_argument("--proxy", help="Proxy URL, applied to both HTTP and HTTPS (e.g., http://127.0.0.1:8080)")
    parser.add_argument("--no-verify", action="store_true", help="Disable TLS verification")
    parser.add_argument("--follow-redirects", action="store_true", help="Follow HTTP redirects")

    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent requests (default: 10)")
    parser.add_argument("--retries", type=int, default=2, help="Retry count on failure (default: 2)")
    parser.add_argument("--backoff-ms", type=int, default=200, help="Exponential backoff base in ms (default: 200)")
    parser.add_argument("--delay-ms", type=int, default=0, help="Delay between attempts in ms (default: 0)")

    parser.add_argument("--output", help="Write JSONL results to this path")
    parser.add_argument("--save-dir", help="Directory to save per-request meta and response body files")
    parser.add_argument("--save-body", action="store_true", help="Save response bodies when --save-dir is used")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    try:
        args = parser.parse_args(argv)
        run_concurrent_requests(args)
        return 0
    except KeyboardInterrupt:
        print("Interrupted")
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())