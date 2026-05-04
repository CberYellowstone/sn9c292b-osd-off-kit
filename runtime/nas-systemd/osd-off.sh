#!/bin/sh

TESTAP=/opt/sn9c292b/SONiX_UVC_TestAP
LOG=/tmp/sn9c292b_osd_off.log
WAIT_SECONDS=${SN9C292B_OSD_WAIT_SECONDS:-20}
VENDOR_ID=0c45
MODEL_ID=6366

log() {
  echo "[$(date -Is)] $*" >> "$LOG"
}

is_target_video() {
  dev=$1
  props=$(udevadm info -q property -n "$dev" 2>/dev/null || true)
  echo "$props" | grep -q "^ID_VENDOR_ID=$VENDOR_ID$" || return 1
  echo "$props" | grep -q "^ID_MODEL_ID=$MODEL_ID$" || return 1
  return 0
}

try_osd_off() {
  dev=$1

  "$TESTAP" -a "$dev" >> "$LOG" 2>&1 || true

  if "$TESTAP" --xuset-oe 0,0 "$dev" >> "$LOG" 2>&1; then
    log "OSD off succeeded on $dev"
    return 0
  fi

  log "OSD off failed on $dev"
  return 1
}

: > "$LOG"
log "starting OSD off probe"

if [ ! -x "$TESTAP" ]; then
  log "missing $TESTAP"
  exit 0
fi

i=0
rounds_after_first_match=0
successes=0
attempts=0

while [ "$i" -lt "$WAIT_SECONDS" ]; do
  found_match=0

  for dev in /dev/video*; do
    [ -e "$dev" ] || continue
    is_target_video "$dev" || continue

    found_match=1
    attempts=$((attempts + 1))

    if try_osd_off "$dev"; then
      successes=$((successes + 1))
    fi
  done

  if [ "$found_match" -eq 1 ]; then
    rounds_after_first_match=$((rounds_after_first_match + 1))
    if [ "$rounds_after_first_match" -ge 2 ]; then
      break
    fi
  fi

  i=$((i + 1))
  sleep 1
done

log "OSD off probe finished: attempts=$attempts successes=$successes"
exit 0
