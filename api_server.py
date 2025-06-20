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
    try:
        print("🔓 Starting scraper")
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()

            # 1️⃣ Login
            print("🌐 Navigating to login")
            page.goto("https://app.maddox.ai/login")
            page.fill("#login-email-input", creds.email)
            page.fill("#login-password-input", creds.password)
            time.sleep(1.5)

            print("🔍 Clicking Login/Anmelden")
            for label in ("Login", "Anmelden"):
                btn = page.locator(f"button:has-text('{label}')")
                if btn.is_visible(timeout=7000):
                    btn.click(force=True)
                    print(f"✅ Clicked '{label}'")
                    break
            else:
                raise RuntimeError("Login button not found")

            # 2️⃣ Wait & click Monitor
            print("⏳ Waiting for sidebar")
            time.sleep(3)
            monitor_btn = page.locator('[data-testid="main-menu-monitor"]')
            monitor_btn.wait_for(state="attached", timeout=15000)
            print("🔍 Scrolling Monitor into view")
            monitor_btn.scroll_into_view_if_needed()
            print("🔍 Force-clicking Monitor")
            monitor_btn.click(force=True)
            print("✅ Monitor clicked")

            # 3️⃣ Wait for Monitor page
            print("⏳ Waiting for /monitor URL")
            page.wait_for_url("**/monitor**", timeout=15000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            print("✅ Monitor page loaded")

            # 4️⃣ Extract KPI
            print("🔍 Extracting 'Items inspected'")
            span = page.locator(
                "div:has(h5:text-is('Items inspected')) span[aria-label*='items inspected']"
            )
            value = "(not available)"
            for i in range(3):
                span.wait_for(state="attached", timeout=7000)
                aria = span.get_attribute("aria-label") or ""
                if aria.strip() and aria[0].isdigit():
                    value = aria.split()[0]
                    print(f"📊 Found: {value}")
                    break
                print(f"⏳ Attempt {i+1}: aria-label={aria!r}")
                time.sleep(3)

            browser.close()
        print("✅ Scrape complete")
        return {"items_inspected": value}

    except Exception as e:
        print("❌ Error during scrape:", e)
        raise HTTPException(status_code=500, detail=str(e))

