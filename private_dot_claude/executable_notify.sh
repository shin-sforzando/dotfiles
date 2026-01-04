#!/bin/bash

input=$(cat)
cwd=$(echo "$input" | jq -r '.cwd')
project=$(basename "$cwd")
notification_type=$(echo "$input" | jq -r '.notification_type')

case "$notification_type" in
  "permission_prompt")
    terminal-notifier -title "Claude Code" -subtitle "$project" -message "Awaiting approval ..." -sound "Ping"
    ;;
  "idle_prompt")
    terminal-notifier -title "Claude Code" -subtitle "$project" -message "Waiting for input ..." -sound "Purr"
    ;;
  "stop")
    terminal-notifier -title "Claude Code" -subtitle "$project" -message "Task completed!" -sound "Glass"
    ;;
  *)
    terminal-notifier -title "Claude Code" -subtitle "$project" -message "Notification" -sound default
    ;;
esac
