# HTTP Runner (Safe)

This repository includes a safe, terminal-friendly HTTP runner CLI that lets you make concurrent requests with full control over headers, cookies, params, HTTP methods, retries, proxies, TLS verification, and output.

It does not target or circumvent private APIs.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Show help:

```bash
python http_runner.py --help
```

Basic GET:

```bash
python http_runner.py --url https://httpbin.org/get --param foo=bar --header "X-Example: 123"
```

POST JSON:

```bash
python http_runner.py --url https://httpbin.org/post --method POST --json '{"hello":"world"}'
```

Concurrent requests using a session file:

```bash
# sessions.txt contains one token per line
# Use the token as a cookie named "sessionid"
python http_runner.py \
  --url https://httpbin.org/anything \
  --method GET \
  --session-file sessions.txt \
  --session-cookie-name sessionid \
  --concurrency 20 \
  --retries 2 \
  --backoff-ms 200 \
  --output results.jsonl \
  --save-dir responses \
  --save-body
```

Proxy and TLS options:

```bash
python http_runner.py --url https://httpbin.org/get --proxy http://127.0.0.1:8080 --no-verify
```

Parameters and cookies can be repeated:

```bash
python http_runner.py \
  --url https://httpbin.org/get \
  --param a=1 --param b=2 \
  --cookie foo=bar --cookie baz=qux
```

Notes:
- Provide either `--json` or `--data`, not both.
- When using `--save-dir`, the CLI writes `<name>.meta.json` and optionally `<name>.body` per request.
- In single-request mode (no `--session-file`), you can set `--name` to control the output filenames.