"""
ThreePaths - Net Worth Tracker
Si A: Software Engineer Jakarta Rp 10jt/bulan
Si B: Software Engineer Jakarta Rp 6jt/bulan
Si C: Full-time Trader Bandung (manual input)
"""
import os
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# === CONFIG ===
BOT_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID      = os.environ.get("TELEGRAM_CHAT_ID", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

SALARY_DAY = 25

CHARACTERS = {
    "A": {"name": "Si A", "city": "Jakarta", "income": 10_000_000, "expense": 6_000_000},
    "B": {"name": "Si B", "city": "Jakarta", "income": 6_000_000,  "expense": 3_750_000},
    "C": {"name": "Si C", "city": "Bandung",  "income": None,       "expense": 3_900_000},
}

JOBS = {"daily"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("threepaths")


# === SUPABASE ===
class Supabase:
    def __init__(self, url, key):
        self.url = url.rstrip("/") if url else ""
        self.headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def get_all(self):
        r = requests.get(f"{self.url}/rest/v1/threepaths?select=*", headers=self.headers, timeout=15)
        r.raise_for_status()
        rows = r.json()
        return {row["key"]: row for row in rows}

    def update(self, key, payload):
        r = requests.patch(
            f"{self.url}/rest/v1/threepaths?key=eq.{key}",
            headers=self.headers, json=payload, timeout=15
        )
        r.raise_for_status()


# === TELEGRAM ===
class Telegram:
    def __init__(self, token, chat_id):
        self.base = f"https://api.telegram.org/bot{token}"
        self.chat_id = chat_id

    def send(self, text):
        r = requests.post(f"{self.base}/sendMessage", json={
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }, timeout=30)
        if not r.ok:
            log.error("Telegram error: %s", r.text)
        r.raise_for_status()
        return r.json()


# === HELPERS ===
def fmt_rp(amount):
    if amount is None:
        return "❓"
    if amount >= 1_000_000_000:
        return f"Rp {amount/1_000_000_000:.2f}M"
    if amount >= 1_000_000:
        return f"Rp {amount/1_000_000:.1f}jt"
    return f"Rp {amount:,.0f}"


# === JOB: DAILY ===
def daily(sb, tg):
    data = sb.get_all()
    today = datetime.now()
    month_key = f"{today.year}-{today.month:02d}"

    # Auto add salary for A & B on salary day
    for key in ["A", "B"]:
        row = data[key]
        if today.day >= SALARY_DAY and row.get("last_salary_month") != month_key:
            char = CHARACTERS[key]
            savings = char["income"] - char["expense"]
            new_nw = int(row["net_worth"]) + savings
            sb.update(key, {"net_worth": new_nw, "last_salary_month": month_key})
            data[key]["net_worth"] = new_nw
            data[key]["last_salary_month"] = month_key
            log.info("[%s] Salary added: +%s", key, savings)

    # Build message
    date_str = today.strftime("%-d %b %Y")
    emojis = {"A": "🔵", "B": "🟣", "C": "🟢"}

    lines = [f"📊 *THREEPATHS — {date_str}*", "―――――――――――――――――――"]

    for key, char in CHARACTERS.items():
        row = data[key]
        nw = int(row["net_worth"])
        inc = row.get("income_this_month") if key == "C" else char["income"]

        lines.append(f"\n{emojis[key]} *{char['name']}* — {char['city']}")
        lines.append(f"💰 Income    : {fmt_rp(inc)}")
        lines.append(f"💸 Expense   : {fmt_rp(char['expense'])}")
        lines.append(f"🏦 Net Worth : *{fmt_rp(nw)}*")

    # Ranking
    ranked = sorted(
        [(k, int(data[k]["net_worth"])) for k in ["A", "B", "C"]],
        key=lambda x: x[1], reverse=True
    )
    lines.append("\n―――――――――――――――――――")
    lines.append("🏆 *RANKING*")
    for medal, (k, nw) in zip(["🥇", "🥈", "🥉"], ranked):
        lines.append(f"{medal} Path {k} — {fmt_rp(nw)}")

    lines.append("\n_Tel-U · Class of '26_")
    tg.send("\n".join(lines))


def run_job(job_name):
    if job_name not in JOBS:
        raise ValueError(f"unknown job: {job_name} (use: {'|'.join(JOBS)})")
    sb = Supabase(SUPABASE_URL, SUPABASE_KEY)
    tg = Telegram(BOT_TOKEN, CHAT_ID)
    if job_name == "daily":
        daily(sb, tg)
