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
    1. Login to app.maddox.ai
    2. Click the Monitor sidebar link
    3. Extract the 'Items inspected' KPI
    """
    try:
        print("🔓 Starting scraper")
        with sync_playwright() as pw:
            browser = pw.chromium.launch()    # headless=True in production
            page = browser.new_page()

            # ─── Step 1: Login ───────────────────────────────────────────────
            print("🌐 Navigating to login page")
            page.goto("https://app.maddox.ai/login")
            page.fill("#login-email-input", creds.email)
            page.fill("#login-password-input", creds.password)
            time.sleep(1.5)

            # Try both English & German buttons
            print("🔍 Trying login buttons")
            clicked = False
            for label in ("Login", "Anmelden"):
                btn = page.locator(f"button:has-text('{label}')")
                if btn.is_visible(timeout=7000):
                    btn.click(force=True)
                    print(f"✅ Clicked '{label}'")
                    clicked = True
                    break
            if not clicked:
                raise RuntimeError("Login button not found")

            # ─── Step 2: Navigate to Monitor ───────────────────────────────────
            print("⏳ Waiting for sidebar to render")
            time.sleep(3)
            print("🔍 Clicking Monitor sidebar link")
            page.click('[data-testid="main-menu-monitor"]', force=True)
            print("✅ Clicked Monitor link")

            print("⏳ Waiting for Monitor page to load")
            page.wait_for_url("**/monitor**", timeout=15000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            print("✅ Monitor page loaded")

            # ─── Step 3: Extract KPI ──────────────────────────────────────────
            print("🔍 Extracting 'Items inspected'")
            span = page.locator(
                "div:has(h5:text-is('Items inspected')) span[aria-label*='items inspected']"
            )
            value = "(not available)"
            for attempt in range(3):
                span.wait_for(state="attached", timeout=7000)
                aria = span.get_attribute("aria-label") or ""
                if aria.strip() and aria.strip()[0].isdigit():
                    value = aria.split()[0]
                    print(f"📊 Found KPI: {value}")
                    break
                print(f"⏳ Attempt {attempt+1}: aria-label={aria!r}")
                time.sleep(3)

            browser.close()
        print("✅ Scrape complete")
        return {"items_inspected": value}

    except Exception as e:
        print("❌ Error during scrape:", e)
        raise HTTPException(status_code=500, detail=str(e))

