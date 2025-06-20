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
    Logs into Maddox.ai, navigates to the Monitor page, and extracts the "Items inspected" KPI.
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

            # 2. Wait for dashboard
            page.wait_for_url("**/monitor", timeout=10000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # 3. Click Monitor in sidebar
            monitor_btn = page.locator('[data-testid="main-menu-Monitor"]')
            monitor_btn.wait_for(state="visible", timeout=5000)
            monitor_btn.click()
            page.wait_for_url("**/monitor", timeout=10000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # 4. Extract KPI
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
