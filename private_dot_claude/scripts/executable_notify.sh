#!/bin/bash

input=$(cat)
cwd=$(echo "$input" | jq -r '.cwd')
project=$(basename "$cwd")
notification_type=$(echo "$input" | jq -r '.notification_type')
message=$(echo "$input" | jq -r '.message // empty')

notify() {
  local title="$1"
  local message="$2"
  local sound="$3"
  local urgency="${4:-normal}"

  if [[ -n ${CMUX_WORKSPACE_ID:-} ]] && [[ -n ${CMUX_SURFACE_ID:-} ]] && command -v cmux &>/dev/null; then
    cmux notify --title "$title" --subtitle "$project" --body "$message"
  elif command -v terminal-notifier &>/dev/null; then
    terminal-notifier -title "$title" -subtitle "$project" -message "$message" -sound "$sound"
  elif command -v notify-send &>/dev/null; then
    notify-send -u "$urgency" "$title ($project)" "$message"
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
