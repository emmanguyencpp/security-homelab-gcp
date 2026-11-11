#!/usr/bin/env bash
# Bước 1: tạo mạng VPC cô lập + firewall chỉ cho phép IP của bạn.
source "$(dirname "$0")/config.sh"

gcloud services enable compute.googleapis.com

gcloud compute networks create "$NET" --subnet-mode=custom
gcloud compute networks subnets create "$SUBNET" \
  --network="$NET" --region="$REGION" --range="$SUBNET_RANGE"

# Trong lab: các máy được nói chuyện tự do với nhau (để quét, khai thác).
gcloud compute firewall-rules create seclab-allow-internal \
  --network="$NET" --direction=INGRESS --action=ALLOW \
  --rules=all --source-ranges="$SUBNET_RANGE"

# Từ ngoài vào: CHỈ SSH qua Google IAP (cần đăng nhập tài khoản Google của bạn).
gcloud compute firewall-rules create seclab-allow-iap-ssh \
  --network="$NET" --direction=INGRESS --action=ALLOW \
  --rules=tcp:22 --source-ranges="$IAP_RANGE"

# Các máy không có IP công khai: dùng Cloud NAT để đi ra Internet (cài gói, tải Docker image).
gcloud compute routers create seclab-router --network="$NET" --region="$REGION"
gcloud compute routers nats create seclab-nat --router=seclab-router --region="$REGION" \
  --auto-allocate-nat-external-ips --nat-all-subnet-ip-ranges

# Không có rule mở 80/3000/8080 ra Internet: web lab xem qua SSH tunnel (xem README).
echo "Xong mạng $NET. Không cổng nào mở ra Internet; SSH chỉ qua IAP."
