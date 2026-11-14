import os
import re
import json
import time
import smtplib
import traceback
import requests
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

# ============ CONFIG ============
EMAIL_TO = "paolo.zapp82@gmail.com"
EMAIL_FROM = os.getenv("EMAIL_FROM", "paolo.zapp82@gmail.com")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

CHECK_SECONDS = 300
SENT_FILE = "sent.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.goaloo.com/"
}

LIVE_URL = "https://live.goaloo.com/soccer"

# ============ UTILS ============
def load_sent():
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_sent(s):
    try:
        with open(SENT_FILE, "w") as f:
            json.dump(list(s), f)
    except Exception as e:
        print(f"Save sent error: {e}", flush=True)

sent_keys = load_sent()

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def parse_handicap(s):
    if not s:
        return None
    s = s.strip().replace(" ", "")
    if s in ("-", "--", "", "None"):
        return None
    s = s.replace("+", "")
    try:
        if "/" in s:
            parts = s.split("/")
            vals = [float(p) for p in parts]
            return sum(vals) / len(vals)
        return float(s)
    except:
        return None

def send_mail(subject, body):
    if not EMAIL_PASS:
        log(f"MAIL SKIPPED (no EMAIL_PASS): {subject}")
        log(body)
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASS)
            server.send_message(msg)
        log(f"MAIL INVIATA: {subject}")
        return True
    except Exception as e:
        log(f"MAIL ERROR: {e}")
        return False

# ============ GOALOO SCRAPING ============
def get_live_matches():
    matches = []
    try:
        r = requests.get(LIVE_URL, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        rows = soup.select("tr[id^='tr_']")
        if not rows:
            rows = soup.select("table tr")
        for row in rows:
            try:
                rid = row.get("id", "")
                tds = row.find_all("td")
                if len(tds) < 6:
                    continue
                text = row.get_text(" ", strip=True)
                m_min = re.search(r"(\d{1,3})\s*['’]", text)
                if not m_min:
                    continue
                minute = int(m_min.group(1))
                m_score = re.search(r"(\d+)\s*[-:]\s*(\d+)", text)
                if not m_score:
                    continue
                sh = int(m_score.group(1))
                sa = int(m_score.group(2))
                links = row.find_all("a")
                names = [a.get_text(strip=True) for a in links if a.get_text(strip=True)]
                names = [n for n in names if len(n) > 2]
                if len(names) < 2:
                    continue
                home = names[0]
                away = names[1]
                match_id = rid.replace("tr_", "") if rid else f"{home}-{away}"
                for a in links:
                    href = a.get("href", "")
                    mm = re.search(r"(\d{6,})", href)
                    if mm:
                        match_id = mm.group(1)
                        break
                matches.append({
                    "id": str(match_id),
                    "home": home,
                    "away": away,
                    "minute": minute,
                    "sh": sh,
                    "sa": sa,
                })
            except Exception:
                continue
        log(f"Live matches trovati: {len(matches)}")
        return matches
    except Exception as e:
        log(f"get_live_matches ERROR: {e}")
        traceback.print_exc()
        return []

def get_spread_averages(match_id):
    urls = [
        f"https://www.goaloo.com/odds/{match_id}",
        f"https://live.goaloo.com/odds/{match_id}",
        f"https://www.goaloo.com/soccer/odds/{match_id}",
    ]
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200 or len(r.text) < 1000:
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text(" ", strip=True)
            if "Asian" not in text and "Handicap" not in text:
                continue
            op_vals = []
            cu_vals = []
            for tr in soup.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) < 3:
                    continue
                row_text = tr.get_text(" ", strip=True)
                first = tds[0].get_text(strip=True).lower()
                if first not in ("initial", "live"):
                    continue
                hc = None
                if len(tds) >= 4:
                    hc = parse_handicap(tds[2].get_text(strip=True))
                if hc is None:
                    for cand in re.findall(r"-?\d+(?:\.\d+)?/\d+(?:\.\d+)?|-?\d+(?:\.\d+)?", row_text):
                        v = parse_handicap(cand)
                        if v is not None:
                            hc = abs(v)
                            break
                if hc is None:
                    continue
                hc = abs(hc)
                if first == "initial":
                    op_vals.append(hc)
                elif first == "live":
                    cu_vals.append(hc)
            if op_vals and cu_vals:
                op_media = sum(op_vals) / len(op_vals)
                cu_media = sum(cu_vals) / len(cu_vals)
                return round(op_media, 3), round(cu_media, 3)
        except Exception as e:
            log(f"get_spread {match_id} {url} ERROR: {e}")
            continue
    return None, None

# ============ REGOLE VENUS - FINALI ============
def check_rules(m, op, cu):
    minute = m["minute"]
    sh = m["sh"]
    sa = m["sa"]
    if op is None or cu is None:
        return None
    # R5: 15-20, 0-0, OP >= 1, SENZA TOTAL LINE
    if 15 <= minute <= 20 and sh == 0 and sa == 0:
        if abs(op) >= 1:
            return ("R5", "OVER 0.5 HT")
    # R1-R4: solo 50-60
    if 50 <= minute <= 60:
        if cu > op:
            if sh == 0 and sa == 0:
                return ("R1", "OVER 0.5")
            if sh == 1 and sa == 0 and cu >= 0.75:
                return ("R2", "OVER 1.5")
            if sh == 0 and sa == 1 and cu >= 0.75:
                return ("R3", "OVER 1.5")
            if sh == 1 and sa == 1 and cu >= 1:
                return ("R4", "OVER 2.5")
    return None

def run_once():
    matches = get_live_matches()
    for m in matches:
        if not (15 <= m["minute"] <= 20 or 50 <= m["minute"] <= 60):
            continue
        op, cu = get_spread_averages(m["id"])
        if op is None or cu is None:
            log(f"SKIP {m['home']} vs {m['away']} {m['minute']}' {m['sh']}-{m['sa']} - no OP/CU")
            continue
        log(f"CHECK {m['home']} vs {m['away']} {m['minute']}' {m['sh']}-{m['sa']} OP={op} CU={cu}")
        res = check_rules(m, op, cu)
        if not res:
            continue
        regola, segnale = res
        key = f"{m['id']}|{m['minute']}|{m['sh']}-{m['sa']}|{regola}"
        if key in sent_keys:
            log(f"GIÀ INVIATA {key}")
            continue
        subject = f"VENUS {regola} - {m['home']} vs {m['away']} {m['minute']}' {m['sh']}-{m['sa']} - {segnale}"
        body = (
            f"VENUS {regola}\n"
            f"Match: {m['home']} vs {m['away']}\n"
            f"Minuto: {m['minute']}'\n"
            f"Risultato: {m['sh']}-{m['sa']}\n"
            f"OP media (Initial): {op}\n"
            f"CU media (Live): {cu}\n"
            f"Segnale: {segnale}\n"
            f"Match ID Goaloo: {m['id']}\n"
        )
        ok = send_mail(subject, body)
        if ok:
            sent_keys.add(key)
            save_sent(sent_keys)

# ============ MAIN LOOP H24 ============
if __name__ == "__main__":
    log("VENUS GOALOO BOT AVVIATO - OP=Initial media, CU=Live media, R5 senza Total")
    while True:
        try:
            run_once()
        except Exception as e:
            log(f"LOOP ERROR: {e}")
            traceback.print_exc()
        log(f"Attesa {CHECK_SECONDS}s...")
        time.sleep(CHECK_SECONDS)
