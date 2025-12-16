#!/usr/bin/env bash
# .dokku/notify_slack.sh
set -euo pipefail

STATUS="${1:-}"   # expected: start | complete
[ -z "${STATUS}" ] && { echo "Usage: $0 <start|complete>"; exit 2; }

# Slack webhook is provided by Dokku at deploy time
WEBHOOK="${SLACK_WEBHOOK_RELEASES:-}"
[ -z "${WEBHOOK}" ] && { echo "SLACK_WEBHOOK_RELEASES is not set"; exit 0; }  # exit 0 so deploy isn't blocked

# Basic context (all optional except app name)
APP="${DOKKU_APP_NAME:-${APP_NAME:-traders-app}}"
ENVIRONMENT="${APP_ENV:-${ENVIRONMENT:-production}}"
TIMESTAMP="$(date -Iseconds)"

if [ "$STATUS" = "start" ]; then
  header="🚀 Deploy starting"
  color="#5B9CF6"
  text="Deploy starting for ${APP}"
elif [ "$STATUS" = "complete" ]; then
  header="✅ Deploy completed"
  color="#32D296"
  text="Deploy completed for ${APP}"
else
  header="ℹ️ Deploy update"
  color="#AAAAAA"
  text="Deploy update for ${APP}"
fi

# Build a Slack Block Kit payload.
# (Values are constrained to alphanumerics and punctuation; no external jq needed.)
read -r -d '' payload <<EOF || true
{
  "text": "${text}",
  "attachments": [{
    "color": "${color}",
    "blocks": [
      { "type": "header", "text": { "type": "plain_text", "text": "${header}: ${APP}" } },
      { "type": "section",
        "fields": [
          { "type": "mrkdwn", "text": "*App:* ${APP}" },
          { "type": "mrkdwn", "text": "*Environment:* ${ENVIRONMENT}" },
          { "type": "mrkdwn", "text": "*Time:* ${TIMESTAMP}" }
        ]
      }
    ]
  }]
}
EOF

# Post to Slack (silent on success; non-fatal on error)
curl -sS -X POST -H 'Content-type: application/json' --data "${payload}" "${WEBHOOK}" >/dev/null 2>&1 || true
