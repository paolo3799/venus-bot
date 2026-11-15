import os, re, time, smtplib
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright

EMAIL_TO = "paolo.zapp82@gmail.com"
EMAIL_FROM = os.getenv("GMAIL_USER", os.getenv("EMAIL_FROM", "paolo.zapp82@gmail.com"))
EMAIL_PASS = os.getenv("GMAIL_PASS", os.getenv("EMAIL_PASS", ""))
PROXY_SERVER = os.getenv("PROXY_SERVER", "")
PROXY_USER = os.getenv("PROXY_USER", "")
PROXY_PASS = os.getenv("PROXY_PASS", "")

URLS_DA_PROVARE = [
    "https://www.goaloo.com/",
    "https://www.goaloo.com/soccer",
]

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

def parse_handicap(s):
    if not s: return None
    s = s.strip().replace(" ", "").replace("+", "")
    if s in ("-", "--", "", "None"): return None
    try:
        if "/" in s:
            vals = [float(p) for p in s.split("/")]
            return sum(vals) / len(vals)
        return float(s)
    except: return None

def send_mail(subject, body):
    if not EMAIL_PASS:
        log(f"MAIL SKIPPED (no EMAIL_PASS): {subject}"); return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject; msg["From"] = EMAIL_FROM; msg["To"] = EMAIL_TO
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls(); server.login(EMAIL_FROM, EMAIL_PASS); server.send_message(msg)
        log(f"MAIL INVIATA: {subject}"); return True
    except Exception as e:
        log(f"MAIL ERROR: {e}"); return False

def get_live_matches(pg):
    for url in URLS_DA_PROVARE:
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(12000)
            html = pg.content()
            rows = pg.query_selector_all("tr[id^='tr_']")
            log(f"PROVA {url} -> URL finale: {pg.url} | Titolo: {pg.title()} | HTML len={len(html)} | tr_={len(rows)}")
            if len(rows) == 0:
                continue
            matches = []
            for row in rows:
                try:
                    text = row.inner_text()
                    m_min = re.search(r"(\d{1,3})\s*['’]", text)
                    m_score = re.search(r"(\d+)\s*[-:]\s*(\d+)", text)
                    if not m_min or not m_score: continue
                    links = row.query_selector_all("a")
                    names = [a.inner_text().strip() for a in links if len(a.inner_text().strip()) > 2]
                    if len(names) < 2: continue
                    rid = row.get_attribute("id") or ""
                    match_id = rid.replace("tr_", "")
                    for a in links:
                        href = a.get_attribute("href") or ""
                        mm = re.search(r"(\d{6,})", href)
                        if mm: match_id = mm.group(1); break
                    matches.append({"id": str(match_id), "home": names[0], "away": names[1],
                        "minute": int(m_min.group(1)), "sh": int(m_score.group(1)), "sa": int(m_score.group(2))})
                except: continue
            log(f"URL BUONO: {url} | Live matches trovati: {len(matches)}")
            return matches, url
        except Exception as e:
            log(f"PROVA {url} ERROR: {e}")
            continue
    return [], ""

def get_spread_averages(pg, match_id):
    for url in [f"https://www.goaloo.com/odds/{match_id}"]:
        try:
            pg.goto(url, wait_until="domcontentloaded", timeout=30000)
            pg.wait_for_timeout(5000)
            rows = pg.query_selector_all("tr")
            op_vals, cu_vals = [], []
            for tr in rows:
                try:
                    tds = tr.query_selector_all("td")
                    if len(tds) < 3: continue
                    first = tds[0].inner_text().strip().lower()
                    if first not in ("initial", "live"): continue
                    hc = parse_handicap(tds[2].inner_text().strip()) if len(tds) >= 4 else None
                    if hc is None: continue
                    hc = abs(hc)
                    if first == "initial": op_vals.append(hc)
                    else: cu_vals.append(hc)
                except: continue
            if op_vals and cu_vals:
                return round(sum(op_vals)/len(op_vals), 3), round(sum(cu_vals)/len(cu_vals), 3)
        except Exception as e:
            log(f"get_spread {match_id} {url} ERROR: {e}")
    return None, None

def check_rules(m, op, cu):
    minute, sh, sa = m["minute"], m["sh"], m["sa"]
    if op is None or cu is None: return None
    if 15 <= minute <= 20 and sh == 0 and sa == 0:
        if abs(op) >= 1: return ("R5", "OVER 0.5 HT")
    if 50 <= minute <= 60:
        if cu > op:
            if sh == 0 and sa == 0: return ("R1", "OVER 0.5")
            if sh == 1 and sa == 0 and cu >= 0.75: return ("R2", "OVER 1.5")
            if sh == 0 and sa == 1 and cu >= 0.75: return ("R3", "OVER 1.5")
            if sh == 1 and sa == 1 and cu >= 1: return ("R4", "OVER 2.5")
    return None

if __name__ == "__main__":
    log(f"PROXY configurato: {'SI' if PROXY_SERVER else 'NO'}")
    proxy_cfg = None
    if PROXY_SERVER:
        proxy_cfg = {"server": PROXY_SERVER}
        if PROXY_USER: proxy_cfg["username"] = PROXY_USER
        if PROXY_PASS: proxy_cfg["password"] = PROXY_PASS
    with sync_playwright() as p:
        launch_kwargs = {"headless": True, "args": ["--no-sandbox"]}
        if proxy_cfg: launch_kwargs["proxy"] = proxy_cfg
        b = p.chromium.launch(**launch_kwargs)
        pg = b.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
        matches, base_url = get_live_matches(pg)
        lines = []
        for m in matches:
            if not (15 <= m["minute"] <= 20 or 50 <= m["minute"] <= 60): continue
            op, cu = get_spread_averages(pg, m["id"])
            if op is None or cu is None:
                log(f"SKIP {m['home']} vs {m['away']} {m['minute']}' {m['sh']}-{m['sa']} - no OP/CU"); continue
            log(f"CHECK {m['home']} vs {m['away']} {m['minute']}' {m['sh']}-{m['sa']} OP={op} CU={cu}")
            res = check_rules(m, op, cu)
            if res:
                lines.append(f"{res[0]} {m['home']} vs {m['away']} {m['minute']}' {m['sh']}-{m['sa']} OP={op} CU={cu} -> {res[1]}")
        b.close()
    send_mail(f"TEST VENUS - {len(matches)} partite live viste - {len(lines)} segnali - URL: {base_url}",
        f"URL buono: {base_url}\nPartite viste: {len(matches)}\n\nPrime 30:\n" + "\n".join([f"{m['minute']}' {m['home']} {m['sh']}-{m['sa']} {m['away']}" for m in matches[:30]]) +
        f"\n\nSegnali R1-R5:\n" + ("\n".join(lines) if lines else "Nessun segnale in 15-20 / 50-60"))
