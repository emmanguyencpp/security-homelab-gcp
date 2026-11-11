#!/usr/bin/env bash
# Xóa toàn bộ lab. Không hoàn tác được.
source "$(dirname "$0")/config.sh"
read -r -p "Xóa toàn bộ seclab trong project $PROJECT_ID? (gõ yes) " ok
[[ "$ok" == "yes" ]] || exit 0
gcloud compute instances delete "$ATTACKER" "$TARGET" --zone="$ZONE" --quiet || true
gcloud compute routers nats delete seclab-nat --router=seclab-router --region="$REGION" --quiet || true
gcloud compute routers delete seclab-router --region="$REGION" --quiet || true
gcloud compute firewall-rules delete seclab-allow-internal seclab-allow-iap-ssh --quiet || true
gcloud compute networks subnets delete "$SUBNET" --region="$REGION" --quiet || true
gcloud compute networks delete "$NET" --quiet || true
echo "Đã xóa lab."
