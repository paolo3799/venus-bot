import re, time, smtplib, os
from email.message import EmailMessage
from playwright.sync_api import sync_playwright

URL = "https://www.asianbetsoccer.com/livescore.html"
TO = os.environ.get("GMAIL_USER")
FROM = os.environ.get("GMAIL_USER")
PROXY = {"server": os.environ.get("PROXY_SERVER",""), "username": os.environ.get("PROXY_USER",""), "password": os.environ.get("PROXY_PASS","")}

def mail(ogg, testo):
    try:
        m = EmailMessage()
        m["From"] = FROM
        m["To"] = TO
        m["Subject"] = ogg
        m.set_content(testo)
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
            s.starttls()
            s.login(FROM, os.environ.get("GMAIL_PASS","").replace(" ",""))
            s.send_message(m)
        print(f"EMAIL INVIATA: {ogg}", flush=True)
    except Exception as e:
        print(f"Errore mail: {e}", flush=True)

def check(minuto, ris, scu, sop, tcu, top, rh, ra):
    if minuto is None or ris is None: return None
    if rh > 0 or ra > 0: return None
    if scu is None or sop is None: return None
    if 50 <= minuto <= 54 and ris == "0-0":
        if (scu > 0 and scu > sop) or (scu < 0 and scu < sop):
            return ("R1", "OVER 0.5")
    if 50 <= minuto <= 54 and ris == "1-0":
        if (scu > 0 and scu > sop and scu >= 0.75) or (scu < 0 and scu < sop and scu <= -0.75):
            return ("R2", "OVER 1.5")
    if 50 <= minuto <= 54 and ris == "0-1":
        if (scu > 0 and scu > sop and scu >= 0.75) or (scu < 0 and scu < sop and scu <= -0.75):
            return ("R3", "OVER 1.5")
    if 50 <= minuto <= 54 and ris == "1-1":
        if (scu > 0 and scu > sop and scu >= 1) or (scu < 0 and scu < sop and scu <= -1):
            return ("R4", "OVER 2.5")
    if 15 <= minuto <= 19 and ris == "0-0":
        if tcu is not None and top is not None and abs(sop) >= 1 and tcu >= 3:
            return ("R5", "OVER 0.5 HT")
    return None

def fnum(s):
    try: return float(str(s).replace(",", ".").strip())
    except: return None

def get_matches():
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, proxy=PROXY, args=["--no-sandbox", "--disable-dev-shm-usage"])
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        try:
            pg.goto(URL, timeout=60000)
            time.sleep(3)
            for sel in ["#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll","text=Accetta tutto","text=Consenti tutto","text=Accetta","text=Allow all","text=Accept all","#onetrust-accept-btn-handler"]:
                try:
                    pg.locator(sel).first.click(timeout=1000)
                    time.sleep(0.5)
                except: pass
            for _ in range(4):
                pg.mouse.wheel(0, 4000)
                time.sleep(1.5)
                pg.mouse.wheel(0, 4000)
                time.sleep(1.5)
            tables = pg.evaluate("""() => {
                return [...document.querySelectorAll('table')].map(tb => {
                    let rows = [...tb.querySelectorAll('tr')].map(tr => [...tr.querySelectorAll('td')].map(td => ({t: td.innerText.trim(), h: td.outerHTML})));
                    return {txt: tb.innerText.slice(0, 400), rows: rows};
                });
            }""")
            print(f"DEBUG - Tabelle: {len(tables)}", flush=True)
            all_rows = []
            for tb in tables: all_rows.extend(tb["rows"])
            print(f"DEBUG - Righe totali: {len(all_rows)}", flush=True)
            def extract_pairs_from_rows(rows):
                pr = []
                for j in range(len(rows) - 1):
                    if len(rows[j]) > 1 and rows[j][0]["t"] == "H" and len(rows[j + 1]) > 1 and rows[j + 1][0]["t"] == "A":
                        pr.append((rows[j], rows[j + 1]))
                return pr
            odds_tb = None
            best_o = -1
            for tb in tables:
                pairs = extract_pairs_from_rows(tb["rows"])
                score = 0
                for (oh, oa) in pairs:
                    v1 = fnum(oh[1]["t"]) if len(oh) > 1 else None
                    v2 = fnum(oh[2]["t"]) if len(oh) > 2 else None
                    if v1 is not None and v2 is not None and abs(v1) <= 3 and abs(v2) <= 3 and len(oh[1]["t"]) <= 6:
                        score += 1
                if score > best_o:
                    best_o = score
                    odds_tb = tb
            odds_pairs = extract_pairs_from_rows(odds_tb["rows"]) if odds_tb else []
            print(f"PAIRS odds={len(odds_pairs)} score={best_o}", flush=True)
            lega = ""
            idx_pair = -1
            i = 0
            while i < len(all_rows):
                row = all_rows[i]
                if len(row) == 1 and row[0]["t"]:
                    txt = re.sub(r"\s+", " ", row[0]["t"]).strip()
                    if len(txt) > 3 and "http" not in txt and "Min" not in txt:
                        lega = txt
                    i += 1
                    continue
                if len(row) > 1 and row[0]["t"] == "H" and i + 1 < len(all_rows) and all_rows[i + 1] and all_rows[i + 1][0]["t"] == "A":
                    nome_test = row[1]["t"] if len(row) > 1 else ""
                    if nome_test and re.match(r"^-?[\d\.]+$", nome_test.strip()):
                        i += 2
                        continue
                    idx_pair += 1
                    rh = all_rows[i]
                    ra = all_rows[i + 1]
                    casa = re.sub(r"^\d+\s*", "", rh[1]["t"]).strip() if len(rh) > 1 else ""
                    osp = re.sub(r"^\d+\s*", "", ra[1]["t"]).strip() if len(ra) > 1 else ""
                    minuto = None
                    m = re.search(r"(\d+)", rh[2]["t"] if len(rh) > 2 else "")
                    if m: minuto = int(m.group(1))
                    gol_h = rh[3]["t"] if len(rh) > 3 else ""
                    gol_a = ra[2]["t"] if len(ra) > 2 else ""
                    ris = f"{gol_h}-{gol_a}" if gol_h.isdigit() and gol_a.isdigit() else None
                    if ris is None and len(ra) >= 5 and "-" in str(ra[4]["t"]):
                        ris = str(ra[4]["t"]).strip()
                    rossi_h = len(re.findall(r"redcard", rh[1]["h"], re.I)) if len(rh) > 1 else 0
                    rossi_a = len(re.findall(r"redcard", ra[1]["h"], re.I)) if len(ra) > 1 else 0
                    sop = scu = top = tcu = None
                    if idx_pair < len(odds_pairs):
                        oh = odds_pairs[idx_pair][0]
                        sop = fnum(oh[1]["t"]) if len(oh) > 1 else None
                        scu = fnum(oh[2]["t"]) if len(oh) > 2 else None
                        top = fnum(oh[6]["t"]) if len(oh) > 6 else None
                        tcu = fnum(oh[7]["t"]) if len(oh) > 7 else None
                    out.append({"lega": lega, "casa": casa, "osp": osp, "minuto": minuto, "ris": ris, "rossi_h": rossi_h, "rossi_a": rossi_a, "sop": sop, "scu": scu, "top": top, "tcu": tcu})
                    i += 2
                    continue
                i += 1
        except Exception as e:
            print(f"Errore in get_matches: {e}", flush=True)
        finally:
            b.close()
    return out

print("VENUS GitHub - 1 giro", flush=True)
matches = get_matches()
print(f"Partite estratte: {len(matches)}", flush=True)
for m in matches:
    print(f"[{m['lega']}] {m['casa']} vs {m['osp']} | Min:{m['minuto']} Ris:{m['ris']} Rossi:{m['rossi_h']}/{m['rossi_a']} Spread OP:{m['sop']} CU:{m['scu']} Total OP:{m['top']} CU:{m['tcu']}", flush=True)
    res = check(m['minuto'], m['ris'], m['scu'], m['sop'], m['tcu'], m['top'], m['rossi_h'], m['rossi_a'])
    if res:
        regola, over = res
        mail(f"[{regola}] {m['casa']} vs {m['osp']} - {over}", f"Lega: {m['lega']}\nMatch: {m['casa']} vs {m['osp']}\nMinuto: {m['minuto']}\nRisultato: {m['ris']}\nRossi Casa: {m['rossi_h']} Rossi Ospite: {m['rossi_a']}\nSpread OP: {m['sop']} CU: {m['scu']}\nTotal OP: {m['top']} CU: {m['tcu']}\nSegnale: {over}")
print("--- fine giro ---", flush=True)
