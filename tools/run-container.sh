#!/usr/bin/env bash
set -euo pipefail
task_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
task_image=localhost/ro-plasma-setup-harness:6.7.5-1.fc44
if [[ ${1:-} == build ]]; then
    exec podman build --file "$task_root/containers/Containerfile" --tag "$task_image" "$task_root"
fi
if [[ ${1:-} != test || $# != 1 ]]; then
    echo 'Usage: bash tools/run-container.sh build | test' >&2
    exit 2
fi
# No bind mounts, host display, D-Bus, devices, or host HOME. Output is JSON on
# stdout; redirect it to a report file if desired. Tests run as an ordinary UID.
exec podman run --rm --network=none --read-only --cap-drop=ALL \
    --security-opt=no-new-privileges --tmpfs /tmp:rw,nosuid,nodev,size=128m \
    --env QT_QPA_PLATFORM=offscreen --env QSG_RHI_BACKEND=software "$task_image"
