#!/usr/bin/env bash
# Tắt máy khi không dùng để tiết kiệm credit (ổ đĩa vẫn giữ).
# Bật lại: thay "stop" bằng "start".
source "$(dirname "$0")/config.sh"
ACTION="${1:-stop}"
gcloud compute instances "$ACTION" "$ATTACKER" "$TARGET" --zone="$ZONE"
