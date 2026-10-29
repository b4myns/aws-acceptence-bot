# AWS Cloud Club acceptance bot

This script reads candidate rows from Google Sheets, creates one-use Discord invites, and sends acceptance emails.

## Setup

1. Install Python 3.10 or newer.
2. Install dependencies: `python -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and fill in the Discord, Google Sheets, and SMTP settings.
4. Place the Google service account JSON at the path in `GOOGLE_CREDENTIALS_FILE` (default: `credentials.json`). Share the spreadsheet with the service account email from that JSON file.
5. Run `python send_aws_acceptances_auto_discord.py`.

`.env` and `credentials.json` are excluded by `.gitignore`; never commit them. Do not put secrets in source code or issue comments.