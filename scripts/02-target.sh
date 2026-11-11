#!/usr/bin/env bash
# Bước 2: máy mục tiêu chạy các ứng dụng CỐ Ý CÓ LỖ HỔNG để luyện tập hợp pháp.
#   - OWASP Juice Shop  : cổng 3000
#   - DVWA              : cổng 8080
# Máy này KHÔNG có IP công khai -> không ai ngoài lab chạm tới được.
source "$(dirname "$0")/config.sh"

gcloud compute instances create "$TARGET" \
  --zone="$ZONE" --machine-type="$MACHINE" \
  --subnet="$SUBNET" --private-network-ip="$TARGET_IP" --no-address \
  --image-family=debian-12 --image-project=debian-cloud \
  --boot-disk-size=20GB --labels=lab=seclab,role=target \
  --metadata=startup-script='#!/bin/bash
set -e
if ! command -v docker >/dev/null; then
  apt-get update && apt-get install -y docker.io
fi
systemctl enable --now docker
docker rm -f juice-shop dvwa 2>/dev/null || true
docker run -d --restart unless-stopped --name juice-shop -p 3000:3000 bkimminich/juice-shop
docker run -d --restart unless-stopped --name dvwa -p 8080:80 vulnerables/web-dvwa
'

echo "Máy mục tiêu $TARGET ($TARGET_IP) đang khởi động, đợi 3-5 phút để Docker tải image."
