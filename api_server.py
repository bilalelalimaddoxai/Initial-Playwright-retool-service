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
    Logs into Maddox.ai, clicks through to the Monitor page, 
    and extracts the "Items inspected" KPI.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            # 1. Login
            page.goto("https://app.maddox.ai/login")
            page.fill("#login-email-input", creds.email)
            page.fill("#login-password-input", creds.password)
            time.sleep(1.5)
            page.press("#login-password-input", "Enter")
            for label in ("Login", "Anmelden"):
                btn = page.locator(f"button:has-text('{label}')")
                if btn.is_visible():
                    btn.click(force=True)
                    break

            # 2. Wait for the sidebar Monitor button and click it
            page.wait_for_selector('[data-testid="main-menu-Monitor"]', timeout=15000)
            time.sleep(1)  # let any animations finish
            monitor_btn = page.locator('[data-testid="main-menu-Monitor"]')
            monitor_btn.click(force=True)
            print("✅ Clicked Monitor button in sidebar")

            # 3. Now wait for the Monitor page to load
            page.wait_for_url("**/monitor**", timeout=15000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # 4. Extract KPI: Items inspected
            span = page.locator(
                "div:has(h5:text-is('Items inspected')) span[aria-label*='items inspected']"
            )
            value = "(not available)"
            for _ in range(3):
                aria = span.get_attribute("aria-label") or ""
                if aria.strip() and aria.strip()[0].isdigit():
                    value = aria.split()[0]
                    break
                time.sleep(2)

            browser.close()

        return {"items_inspected": value}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
