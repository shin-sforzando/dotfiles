#!/bin/bash

input=$(cat)
cwd=$(echo "$input" | jq -r '.cwd')
project=$(basename "$cwd")
app_icon="https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Claude_AI_symbol.svg/250px-Claude_AI_symbol.svg.png"
notification_type=$(echo "$input" | jq -r '.notification_type')

case "$notification_type" in
  "permission_prompt")
    terminal-notifier -title "Claude Code" -subtitle "$project" -message "Awaiting approval ..." -appIcon "$app_icon" -sender "com.anthropic.claudefordesktop" -sound "Ping"
    ;;
  "idle_prompt")
    terminal-notifier -title "Claude Code" -subtitle "$project" -message "Waiting for input ..." -appIcon "$app_icon" -sender "com.anthropic.claudefordesktop" -sound "Purr"
    ;;
  "stop")
    terminal-notifier -title "Claude Code" -subtitle "$project" -message "Task completed!" -appIcon "$app_icon" -sender "com.anthropic.claudefordesktop" -sound "Glass"
    ;;
  *)
    terminal-notifier -title "Claude Code" -subtitle "$project" -message "Notification" -appIcon "$app_icon" -sender "com.anthropic.claudefordesktop" -sound default
    ;;
esac
