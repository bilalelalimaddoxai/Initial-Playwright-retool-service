from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import time

app = FastAPI()

class Credentials(BaseModel):
    email: str
    password: str

@app.post("/scrape/items-inspected")
def scrape_items_inspected(creds: Credentials):
    """
    1️⃣ Open login page  
    2️⃣ Fill credentials & click Login/Anmelden  
    3️⃣ Wait, click Monitor in sidebar  
    4️⃣ Wait for Monitor view  
    5️⃣ Extract 'Items inspected' KPI
    """
    try:
        print("🔓 Starting scraper")
        with sync_playwright() as pw:
            browser = pw.chromium.launch()  # headless=True in prod
            page = browser.new_page()

            # ─── Step 1: Open login page ────────────────────────────────
            print("🌐 Navigating to login page")
            page.goto("https://app.maddox.ai/login")

            # ─── Step 2: Fill credentials ───────────────────────────────
            page.fill("#login-email-input", creds.email)
            page.fill("#login-password-input", creds.password)
            time.sleep(1.5)

            # ─── Step 3: Click Login/Anmelden ──────────────────────────
            login_clicked = False
            for label in ("Login", "Anmelden"):
                btn = page.locator(f"button:has-text('{label}')")
                if btn.is_visible(timeout=7000):
                    print(f"🔍 Trying login button: {label}")
                    btn.click(force=True)
                    print(f"✅ Clicked '{label}' button")
                    login_clicked = True
                    break
            if not login_clicked:
                raise RuntimeError("Login button not found (neither 'Login' nor 'Anmelden').")

            print("⏳ Waiting for dashboard to settle")
            time.sleep(2)

            # ─── Step 4: Click Monitor sidebar link ────────────────────
            print("🔍 Looking for Monitor sidebar link")
            time.sleep(3)  # give Render extra time to render the sidebar
            page.click('[data-testid="main-menu-Monitor"]', force=True)
            print("✅ Clicked Monitor button")

            print("⏳ Waiting for Monitor page to load")
            page.wait_for_url("**/monitor**", timeout=15000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            print("✅ Monitor page loaded")

            # ─── Step 5: Extract KPI: Items inspected ─────────────────
            print("🔍 Extracting 'Items inspected' KPI")
            span = page.locator(
                "div:has(h5:text-is('Items inspected')) span[aria-label*='items inspected']"
            )
            value = "(not available)"
            for attempt in range(3):
                span.wait_for(state="attached", timeout=5000)
                aria = span.get_attribute("aria-label") or ""
                if aria.strip() and aria.strip()[0].isdigit():
                    value = aria.split()[0]
                    print(f"📊 Items inspected found: {value}")
                    break
                print(f"⏳ Attempt {attempt+1}: KPI not ready → aria-label={aria!r}")
                time.sleep(3)

            browser.close()
        print("✅ Scrape complete")
        return {"items_inspected": value}

    except Exception as e:
        print("❌ Error during scrape:", e)
        raise HTTPException(status_code=500, detail=str(e))


