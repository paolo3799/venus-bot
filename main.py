from playwright.sync_api import sync_playwright

print("TEST GOALOO PLAYWRIGHT - inizio", flush=True)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
        print("Apro https://www.goaloo.com/", flush=True)
        page.goto("https://www.goaloo.com/", timeout=60000)
        page.wait_for_timeout(8000)
        text = page.content()
        print(f"Lunghezza pagina renderizzata: {len(text)}", flush=True)

        for squadra in ["Portugal", "Austria", "Real Oviedo", "Sweden", "Girona"]:
            if squadra in text:
                print(f"TROVATA: {squadra}", flush=True)
            else:
                print(f"NON TROVATA: {squadra}", flush=True)

        if "Portugal" in text or "Girona" in text:
            print("RISULTATO: GOALOO FUNZIONA CON BROWSER - possiamo fare Venus", flush=True)
        else:
            print("RISULTATO: ANCORA NIENTE - serve API", flush=True)

        browser.close()
except Exception as e:
    print(f"ERRORE: {type(e).__name__}: {e}", flush=True)

print("TEST FINITO", flush=True)
