#!/usr/bin/env python3
"""ReconKit - công cụ trinh sát nhỏ cho homelab.

Chức năng:
  scan     Quét cổng TCP (connect scan, đa luồng) và lấy banner dịch vụ.
  headers  Kiểm tra các HTTP security header của một trang web.

CHỈ dùng trên hệ thống bạn sở hữu hoặc được cho phép bằng văn bản.
Mặc định công cụ từ chối mục tiêu ngoài dải IP nội bộ / loopback.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import ssl
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from urllib.parse import urlparse

TOP_PORTS = [21, 22, 23, 25, 53, 80, 110, 139, 143, 443, 445, 1433, 3000,
             3306, 3389, 5432, 5900, 6379, 8000, 8080, 8443, 9200, 27017]

SECURITY_HEADERS = {
    "Strict-Transport-Security": "Ép trình duyệt luôn dùng HTTPS",
    "Content-Security-Policy": "Giới hạn nguồn script/style, giảm rủi ro XSS",
    "X-Frame-Options": "Chống clickjacking (nhúng trang vào iframe)",
    "X-Content-Type-Options": "Chặn trình duyệt đoán sai kiểu nội dung (nosniff)",
    "Referrer-Policy": "Giới hạn thông tin URL gửi sang trang khác",
    "Permissions-Policy": "Giới hạn quyền camera, micro, vị trí...",
}
LEAKY_HEADERS = ["Server", "X-Powered-By", "X-AspNet-Version"]


# ---------- an toàn: chỉ cho phép mục tiêu được ủy quyền ----------
def resolve(host: str) -> str:
    return socket.gethostbyname(host)


def is_lab_address(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return addr.is_private or addr.is_loopback


def check_authorized(host: str, authorized: bool) -> str:
    ip = resolve(host)
    if not is_lab_address(ip) and not authorized:
        sys.exit(f"[!] {host} ({ip}) không phải IP nội bộ. Chỉ quét hệ thống bạn được phép; "
                 "nếu đã có giấy phép, thêm --authorized.")
    return ip


# ---------- quét cổng ----------
@dataclass
class PortResult:
    port: int
    state: str
    banner: str = ""


def grab_banner(sock: socket.socket, port: int) -> str:
    """Đợi dịch vụ tự chào (SSH, FTP, SMTP...); nếu im lặng thì thử hỏi kiểu HTTP."""
    def first_line(data: bytes) -> str:
        lines = data.decode(errors="replace").strip().splitlines()
        return lines[0][:120] if lines else ""

    try:
        sock.settimeout(0.4)
        try:
            data = sock.recv(256)
        except socket.timeout:
            data = b""
        if not data:
            sock.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
            data = sock.recv(256)
        return first_line(data)
    except (socket.timeout, OSError):
        return ""


def probe(ip: str, port: int, timeout: float) -> PortResult:
    try:
        with socket.create_connection((ip, port), timeout=timeout) as s:
            s.settimeout(timeout)
            return PortResult(port, "open", grab_banner(s, port))
    except (socket.timeout, ConnectionRefusedError, OSError):
        return PortResult(port, "closed")


def parse_ports(spec: str) -> list[int]:
    if spec == "top":
        return TOP_PORTS
    ports: set[int] = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = map(int, part.split("-"))
            ports.update(range(a, b + 1))
        else:
            ports.add(int(part))
    bad = [p for p in ports if not 0 < p < 65536]
    if bad:
        raise ValueError(f"Cổng không hợp lệ: {bad}")
    return sorted(ports)


def scan(ip: str, ports: list[int], timeout: float, workers: int) -> list[PortResult]:
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = ex.map(lambda p: probe(ip, p, timeout), ports)
    return [r for r in results if r.state == "open"]


# ---------- kiểm tra HTTP header ----------
@dataclass
class HeaderReport:
    url: str
    status: int
    missing: dict[str, str] = field(default_factory=dict)
    present: list[str] = field(default_factory=list)
    leaks: dict[str, str] = field(default_factory=dict)
    score: int = 0


def audit_headers(url: str, timeout: float) -> HeaderReport:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "ReconKit/1.0"})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    except urllib.error.HTTPError as e:  # vẫn có header dù mã lỗi
        resp = e
    headers = {k.lower(): v for k, v in resp.headers.items()}
    rep = HeaderReport(url=url, status=resp.status if hasattr(resp, "status") else resp.code)
    for name, why in SECURITY_HEADERS.items():
        if name.lower() in headers:
            rep.present.append(name)
        else:
            rep.missing[name] = why
    for name in LEAKY_HEADERS:
        if name.lower() in headers:
            rep.leaks[name] = headers[name.lower()]
    rep.score = round(100 * len(rep.present) / len(SECURITY_HEADERS))
    return rep


# ---------- CLI ----------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="reconkit", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--authorized", action="store_true",
                    help="Xác nhận bạn có quyền kiểm thử mục tiêu ngoài mạng nội bộ")
    ap.add_argument("--json", action="store_true", help="In kết quả dạng JSON")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="Quét cổng TCP + lấy banner")
    s.add_argument("host")
    s.add_argument("-p", "--ports", default="top", help='"top", "1-1024" hoặc "22,80,443"')
    s.add_argument("-t", "--timeout", type=float, default=0.8)
    s.add_argument("-w", "--workers", type=int, default=100)

    h = sub.add_parser("headers", help="Kiểm tra HTTP security header")
    h.add_argument("url")
    h.add_argument("-t", "--timeout", type=float, default=5)

    a = ap.parse_args(argv)

    if a.cmd == "scan":
        ip = check_authorized(a.host, a.authorized)
        res = scan(ip, parse_ports(a.ports), a.timeout, a.workers)
        if a.json:
            print(json.dumps([asdict(r) for r in res], ensure_ascii=False, indent=2))
        else:
            print(f"Mục tiêu: {a.host} ({ip}) - {len(res)} cổng mở")
            for r in res:
                print(f"  {r.port:>5}/tcp  open  {r.banner}")
    else:
        host = urlparse(a.url).hostname or ""
        check_authorized(host, a.authorized)
        rep = audit_headers(a.url, a.timeout)
        if a.json:
            print(json.dumps(asdict(rep), ensure_ascii=False, indent=2))
        else:
            print(f"{rep.url}  (HTTP {rep.status})  điểm: {rep.score}/100")
            for n in rep.present:
                print(f"  [+] {n}")
            for n, why in rep.missing.items():
                print(f"  [-] Thiếu {n}: {why}")
            for n, v in rep.leaks.items():
                print(f"  [!] Lộ thông tin qua {n}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
