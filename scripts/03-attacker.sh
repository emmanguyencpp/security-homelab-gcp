#!/usr/bin/env bash
# Bước 3: máy tấn công. Debian + công cụ chính, kèm container Kali đầy đủ.
source "$(dirname "$0")/config.sh"

gcloud compute instances create "$ATTACKER" \
  --zone="$ZONE" --machine-type="$MACHINE" \
  --subnet="$SUBNET" --private-network-ip="$ATTACKER_IP" --no-address \
  --image-family=debian-12 --image-project=debian-cloud \
  --boot-disk-size=40GB --labels=lab=seclab,role=attacker \
  --metadata=startup-script='#!/bin/bash
set -e
if [ -f /opt/seclab-ready ]; then exit 0; fi
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y nmap tshark tcpdump curl jq git python3-pip docker.io
systemctl enable --now docker
docker pull kalilinux/kali-rolling
touch /opt/seclab-ready
'

echo "Máy tấn công $ATTACKER ($ATTACKER_IP) đang khởi động."
echo "Vào máy:   gcloud compute ssh $ATTACKER --zone $ZONE --tunnel-through-iap"
echo "Mở Kali:   sudo docker run -it --rm --net=host kalilinux/kali-rolling bash"
echo "Trong Kali: apt update && apt install -y kali-linux-headless   (Metasploit, sqlmap, nikto...)"
