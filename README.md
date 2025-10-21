# htb-presence

Small script that posts your active HackTheBox machine to Discord Rich Presence.

## Setup

1. Create virtualenv & activate
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

2. Add `.env` (copy `.env.example`)
```bash
cp .env.example .env
# Edit .env and paste your HTB API token
```

3. Run
```bash
python htb_presence.py
```

Notes:
- Use native Discord (not snap/flatpak) for best IPC compatibility.
- Make sure you have an **active machine instance** running on HTB (see below) and you’re connected to the HTB VPN for that region.
- Do NOT commit your `.env`.
