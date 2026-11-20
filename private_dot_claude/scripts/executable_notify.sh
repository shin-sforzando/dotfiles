#!/bin/bash

input=$(cat)
cwd=$(echo "$input" | jq -r '.cwd')
project=$(basename "$cwd")
notification_type=$(echo "$input" | jq -r '.notification_type')
message=$(echo "$input" | jq -r '.message // empty')

osascript_notify() {
  # Pass values via argv so quotes in the message cannot break the AppleScript source
  [[ -x /usr/bin/osascript ]] || return 1
  /usr/bin/osascript \
    -e 'on run argv' \
    -e 'display notification (item 2 of argv) with title (item 1 of argv) subtitle (item 3 of argv) sound name (item 4 of argv)' \
    -e 'end run' \
    "$1" "$2" "$project" "$3" 2>/dev/null
}

notify() {
  local title="$1"
  local message="$2"
  local sound="$3"
  local urgency="${4:-normal}"

  if [[ -n ${CMUX_WORKSPACE_ID:-} ]] && [[ -n ${CMUX_SURFACE_ID:-} ]] && command -v cmux &>/dev/null; then
    cmux notify --title "$title" --subtitle "$project" --body "$message"
  elif command -v terminal-notifier &>/dev/null; then
    # terminal-notifier exits non-zero when macOS notification permission is denied;
    # fall back to osascript instead of losing the notification entirely
    terminal-notifier -title "$title" -subtitle "$project" -message "$message" -sound "$sound" 2>/dev/null ||
      osascript_notify "$title" "$message" "$sound"
  elif command -v notify-send &>/dev/null; then
    timeout 5 notify-send -u "$urgency" "$title ($project)" "$message" 2>/dev/null
  else
    osascript_notify "$title" "$message" "$sound"
  fi
}

case "$notification_type" in
  "permission_prompt")
    notify "Claude Code" "${message:-Awaiting approval ...}" "Ping" "normal"
    ;;
  "idle_prompt")
    notify "Claude Code" "${message:-Waiting for input ...}" "Purr" "low"
    ;;
  "stop")
    notify "Claude Code" "${message:-Task completed!}" "Glass" "normal"
    ;;
  "auth_success")
    notify "Claude Code" "${message:-Authentication successful}" "Glass" "normal"
    ;;
  "elicitation_dialog")
    notify "Claude Code" "${message:-Input required}" "Ping" "critical"
    ;;
  *)
    notify "Claude Code" "${message:-Notification}" "default" "normal"
    ;;
esac

# A failed notification must not surface as a failed Claude Code hook
exit 0
