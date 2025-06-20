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
    Logs into Maddox.ai exactly as in your local script,
    clicks the Monitor sidebar button, and extracts
    the 'Items inspected' KPI.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()       # headless by default
            page = browser.new_page()

            # ─── Step 1: Open login page ────────────────────────────────────────
            page.goto("https://app.maddox.ai/login")

            # ─── Step 2: Fill in credentials ──────────────────────────────────
            page.fill("#login-email-input", creds.email)
            page.fill("#login-password-input", creds.password)

            # Small wait to let React UI finish rendering
            time.sleep(1.5)

            # ─── Step 3: Try both button labels (English & German) ────────────
            login_clicked = False
            for label in ("Login", "Anmelden"):
                try:
                    btn = page.locator(f"button:has-text('{label}')")
                    btn.wait_for(state="visible", timeout=7000)
                    btn.click(force=True)
                    login_clicked = True
                    break
                except:
                    continue

            if not login_clicked:
                raise RuntimeError("Login button not found (neither 'Login' nor 'Anmelden').")

            # ─── Step 4: Wait for sidebar then click Monitor ────────────────────
            time.sleep(3)  # give Render extra time for the sidebar to mount
            monitor_btn = page.locator('[data-testid="main-menu-Monitor"]')
            monitor_btn.wait_for(state="visible", timeout=10000)
            monitor_btn.click()
            
            # Wait for the Monitor page to actually load
            page.wait_for_url("**/monitor**", timeout=15000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)

            # ─── Step 5: Extract KPI – “Items inspected” ────────────────────────
            span = page.locator(
                "div:has(h5:text-is('Items inspected')) span[aria-label*='items inspected']"
            )
            value = "(not available)"
            for _ in range(3):
                span.wait_for(state="attached", timeout=7000)
                aria = span.get_attribute("aria-label") or ""
                if aria.strip() and aria.strip()[0].isdigit():
                    value = aria.split()[0]
                    break
                time.sleep(3)

            browser.close()
        return {"items_inspected": value}

    except Exception as e:
        # Return the raw error for easier debugging
        raise HTTPException(status_code=500, detail=str(e))

