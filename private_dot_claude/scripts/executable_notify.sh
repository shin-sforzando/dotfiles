#!/bin/bash

input=$(cat)
cwd=$(echo "$input" | jq -r '.cwd')
project=$(basename "$cwd")
notification_type=$(echo "$input" | jq -r '.notification_type')

notify() {
  local title="$1"
  local message="$2"
  local sound="$3"
  local urgency="${4:-normal}"

  if command -v terminal-notifier &>/dev/null; then
    terminal-notifier -title "$title" -subtitle "$project" -message "$message" -sound "$sound"
  elif command -v notify-send &>/dev/null; then
    notify-send -u "$urgency" "$title ($project)" "$message"
  fi
}

case "$notification_type" in
  "permission_prompt")
    notify "Claude Code" "Awaiting approval ..." "Ping" "normal"
    ;;
  "idle_prompt")
    notify "Claude Code" "Waiting for input ..." "Purr" "low"
    ;;
  "stop")
    notify "Claude Code" "Task completed!" "Glass" "normal"
    ;;
  *)
    notify "Claude Code" "Notification" "default" "normal"
    ;;
esac
