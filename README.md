# Security Homelab on Google Cloud

Phòng lab bảo mật cá nhân dựng trên Google Cloud để luyện kiểm thử xâm nhập **hợp pháp**: một máy tấn công (Debian + Kali container) và một máy mục tiêu chạy các ứng dụng cố ý có lỗ hổng (OWASP Juice Shop, DVWA), nằm trong mạng VPC cô lập.

> **Nguyên tắc:** Mọi hoạt động quét và khai thác chỉ nhắm vào các máy trong lab này, do chính tôi sở hữu. Không kiểm thử bất kỳ hệ thống nào khác khi chưa có văn bản cho phép.

## Kiến trúc

```
                 Internet  ✗ (không có cổng nào mở ra ngoài)
                    │
        Google IAP (SSH, cần đăng nhập Google)
                    │
┌───────────── VPC seclab-net · 10.10.0.0/24 ─────────────┐
│                                                          │
│  seclab-attacker 10.10.0.10       seclab-target 10.10.0.20│
│  Debian 12 + Kali (Docker)  ───►  Juice Shop  :3000      │
│  nmap · tshark · metasploit       DVWA        :8080      │
│                                                          │
│            Cloud NAT (chỉ chiều ra, để cài gói)          │
└──────────────────────────────────────────────────────────┘
```

| Thiết kế | Lý do |
|---|---|
| Không máy nào có IP công khai | Ứng dụng có lỗ hổng không bao giờ bị lộ ra Internet |
| SSH chỉ qua Identity-Aware Proxy | Không mở cổng 22 cho cả thế giới, xác thực bằng tài khoản Google |
| Cloud NAT | Máy vẫn tải được gói và Docker image dù không có IP công khai |
| Firewall nội bộ mở hoàn toàn | Cho phép quét và khai thác giữa 2 máy trong lab |

## Cách dựng (chạy trong Cloud Shell)

```bash
git clone https://github.com/emmanguyencpp/security-homelab-gcp && cd security-homelab-gcp
gcloud config set project <PROJECT_ID>
./scripts/01-network.sh     # VPC, firewall, Cloud NAT
./scripts/02-target.sh      # máy mục tiêu: Juice Shop + DVWA
./scripts/03-attacker.sh    # máy tấn công
```

Vào máy tấn công và mở Kali:

```bash
gcloud compute ssh seclab-attacker --zone asia-southeast1-b --tunnel-through-iap
sudo docker run -it --rm --net=host kalilinux/kali-rolling bash
apt update && apt install -y kali-linux-headless
```

Mở Juice Shop trên trình duyệt máy bạn (qua đường hầm SSH, không mở cổng):

```bash
gcloud compute ssh seclab-attacker --zone asia-southeast1-b --tunnel-through-iap \
  -- -L 3000:10.10.0.20:3000 -L 8080:10.10.0.20:8080
# rồi mở http://localhost:3000 và http://localhost:8080
```

Dùng Burp Suite trên máy bạn: đặt Burp làm proxy cho trình duyệt rồi truy cập `localhost:3000`.

## Chi phí

2 máy `e2-medium` + Cloud NAT, khoảng 0,1 USD/giờ cho cả lab khi đang bật (300 USD credit dư cho nhiều tháng nếu tắt máy khi không dùng). **Tắt máy khi không dùng:**

```bash
./scripts/stop.sh          # tắt
./scripts/stop.sh start    # bật lại
./scripts/99-teardown.sh   # xóa hẳn
```

## Nội dung repo

| Thư mục | Nội dung |
|---|---|
| `scripts/` | Script dựng và dọn lab bằng gcloud |
| `tools/reconkit/` | Công cụ Python tự viết: quét cổng, lấy banner, kiểm tra HTTP security header (có kiểm thử tự động) |
| `reports/` | Báo cáo kiểm thử xâm nhập Juice Shop theo OWASP Top 10 |
| `writeups/` | Lời giải các bài CTF (picoCTF, TryHackMe) |

## ReconKit

```bash
cd tools/reconkit
python3 reconkit.py scan 10.10.0.20 -p 1-10000
python3 reconkit.py headers http://10.10.0.20:3000/
python3 -m pytest -q
```

Công cụ **từ chối quét IP công cộng** trừ khi người dùng xác nhận `--authorized`.

## Tác giả

Nguyễn Thị Thùy Hương. Sinh viên ngành Mạng máy tính & Truyền thông dữ liệu, Đại học Kinh tế - Kỹ thuật Công nghiệp (UNETI).
