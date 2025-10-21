#!/usr/bin/env python3
"""
htb_presence.py
Simple HTB -> Discord Rich Presence helper.
Uses HTB app API (app.hackthebox.com) and pypresence for Discord RPC.
"""

import os
import time
import sys
import traceback
from pathlib import Path
from dotenv import load_dotenv
import requests
from pypresence import Presence

# ---- Config / env ----
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

HTB_API_TOKEN = os.getenv("HTB_API_TOKEN")
DISCORD_CLIENT_ID = os.getenv("CLIENT_ID", "1125543074861432864")
API_BASE = os.getenv("HTB_API_BASE", "https://app.hackthebox.com/api/v4")

if not HTB_API_TOKEN:
    print("Error: set HTB_API_TOKEN in .env")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {HTB_API_TOKEN}",
    "User-Agent": "HTB Discord Rich Presence",
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://app.hackthebox.com/",
}

# ---- Small helpers ----
def api_get(path, allow_redirects=False, timeout=8):
    url = API_BASE.rstrip("/") + path
    r = requests.get(url, headers=HEADERS, allow_redirects=allow_redirects, timeout=timeout)
    return r

def get_user_info():
    r = api_get("/user/info")
    if r.status_code != 200:
        raise RuntimeError(f"user/info {r.status_code}: {r.text[:200]}")
    return r.json().get("info")

def get_connection_status():
    r = api_get("/user/connection/status")
    if r.status_code != 200:
        raise RuntimeError(f"connection/status {r.status_code}: {r.text[:200]}")
    return r.json().get("status")

def get_active_machine():
    r = api_get("/machines/active")
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise RuntimeError(f"machines/active {r.status_code}: {r.text[:200]}")
    j = r.json()
    # HTB returns {"info": null} when no active machine
    info = j.get("info")
    return None if not info else info

# ---- Main loop ----
def main():
    print("Starting htb-presence...")
    rpc = Presence(DISCORD_CLIENT_ID)
    connected_rpc = False
    last_machine = None

    while True:
        try:
            # ensure Discord is running locally (pypresence handles socket errors)
            if not connected_rpc:
                try:
                    rpc.connect()
                    connected_rpc = True
                    print("Connected to Discord RPC")
                except Exception as e:
                    print("Discord RPC connect failed, retrying...", e)
                    time.sleep(3)
                    continue

            # HTB checks
            user = None
            try:
                user = get_user_info()
            except Exception as e:
                # If token invalid, show helpful message and exit
                print("Failed to fetch user info:", e)
                raise

            connection = False
            try:
                connection = get_connection_status()
            except Exception as e:
                print("Failed to fetch connection status:", e)
                connection = False

            active = get_active_machine()  # None or object
            if not active:
                if last_machine is not None:
                    print("No active machine found -> clearing RPC")
                    rpc.clear()
                    last_machine = None
                # Show a default connected state if on VPN and logged in
                if connection:
                    rpc.update(details="Connected to HTB", state="Waiting for active machine", large_text="Hack The Box")
                time.sleep(5)
                continue

            # we have an active machine
            machine_name = active.get("name")
            machine_avatar = active.get("avatar") or ""
            machine_avatar = ("https://app.hackthebox.com" + machine_avatar) if machine_avatar.startswith("/") else machine_avatar

            # flags: check user activity list for user/root (fallback - individual setups may vary)
            # Try to fetch profile activity to determine user/root flags
            activity_flags = {"user": False, "root": False}
            try:
                apir = api_get(f"/profile/activity/{user.get('id')}")
                if apir.status_code == 200:
                    act = apir.json().get("profile", {}).get("activity", [])
                    for rec in act:
                        if rec.get("name") == machine_name:
                            typ = rec.get("type")
                            if typ == "user":
                                activity_flags["user"] = True
                            elif typ == "root":
                                activity_flags["root"] = True
            except Exception:
                pass

            user_flag = "🟢" if activity_flags["user"] else "🔴"
            root_flag = "🟢" if activity_flags["root"] else "🔴"

            # Build presence
            details = f"{machine_name}"
            state = f"User: {user_flag} | Root: {root_flag}"
            small_image = ""
            small_text = user.get("name") if user else ""
            large_image = machine_avatar if machine_avatar else "htb_logo"

            # Only update RPC if machine changed, otherwise refresh (avoids spamming)
            if machine_name != last_machine:
                print("Updating presence for:", machine_name)
                rpc.update(details=details, state=state, large_image=large_image,
                           small_image=small_image, small_text=small_text)
                last_machine = machine_name
            else:
                # Refresh timestamp or state every 30s so Discord doesn't stale it
                rpc.update(details=details, state=state, large_image=large_image,
                           small_image=small_image, small_text=small_text)
            time.sleep(10)

        except KeyboardInterrupt:
            print("Exiting.")
            try:
                rpc.clear()
            except: pass
            break
        except Exception as exc:
            print("Error (will retry):", exc)
            traceback.print_exc()
            try:
                rpc.clear()
            except:
                pass
            time.sleep(5)

if __name__ == "__main__":
    main()
