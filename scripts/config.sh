#!/usr/bin/env bash
# Cấu hình chung cho homelab. Sửa các biến dưới đây trước khi chạy.
set -euo pipefail

export PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
export REGION="${REGION:-asia-southeast1}"        # Singapore, gần Việt Nam
export ZONE="${ZONE:-asia-southeast1-b}"
export NET="seclab-net"
export SUBNET="seclab-subnet"
export SUBNET_RANGE="10.10.0.0/24"
export ATTACKER="seclab-attacker"                  # máy tấn công (Debian + Kali container)
export TARGET="seclab-target"                      # máy mục tiêu (Juice Shop, DVWA)
export ATTACKER_IP="10.10.0.10"
export TARGET_IP="10.10.0.20"
export MACHINE="${MACHINE:-e2-medium}"

# Không mở bất kỳ cổng nào ra Internet. SSH đi qua Google IAP (dải IP cố định của Google).
export IAP_RANGE="35.235.240.0/20"

if [[ -z "$PROJECT_ID" ]]; then
  echo "Chưa có PROJECT_ID. Chạy: gcloud config set project <ID>" >&2; exit 1
fi
