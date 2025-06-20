from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import time, os

app = FastAPI()


class Credentials(BaseModel):
    email: str
    password: str


@app.post("/scrape/items-inspected")
def scrape_items_inspected(creds: Credentials):
    """
    1.   open login page
    2.   log in (handles EN / DE buttons)
    3.   click the Monitor entry in the sidebar (even if off-screen)
    4.   grab the “Items inspected” KPI
    """

    try:
        print("🔓  Starting scraper")
        with sync_playwright() as pw:
            browser = pw.chromium.launch()  # headless in Render
            page = browser.new_page()

            # ─── 1) LOGIN ──────────────────────────────────────────────────
            print("🌐  Navigate to login")
            page.goto("https://app.maddox.ai/login")
            page.fill("#login-email-input", creds.email)
            page.fill("#login-password-input", creds.password)
            time.sleep(1.5)

            print("🔍  Click Login / Anmelden")
            for label in ("Login", "Anmelden"):
                btn = page.locator(f"button:has-text('{label}')")
                if btn.is_visible(timeout=7_000):
                    btn.click(force=True)
                    print(f"✅  Clicked '{label}'")
                    break
            else:
                raise RuntimeError("Login button not found")

            # ─── 2) CLICK MONITOR ─────────────────────────────────────────
            print("⏳  Waiting for sidebar to render")
            time.sleep(3)  # Render can be slow

            monitor_btn = page.locator('[data-testid="main-menu-monitor"]')
            monitor_btn.wait_for(state="attached", timeout=20_000)  # attached is enough
            monitor_btn.scroll_into_view_if_needed()
            monitor_btn.click(force=True)
            print("✅  Clicked Monitor (force-click)")

            # ─── 3) WAIT FOR MONITOR VIEW ────────────────────────────────
            page.wait_for_url("**/monitor**", timeout=15_000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            print("✅  Monitor page loaded")

            # ─── 4) EXTRACT KPI ─────────────────────────────────────────
            span = page.locator(
                "div:has(h5:text-is('Items inspected')) "
                "span[aria-label*='items inspected']"
            )

            value = "(not available)"
            for attempt in range(3):
                span.wait_for(state="attached", timeout=7_000)
                aria = span.get_attribute("aria-label") or ""
                if aria.strip() and aria.strip()[0].isdigit():
                    value = aria.split()[0]
                    print(f"📊  Items inspected = {value}")
                    break
                print(f"⏳  Attempt {attempt+1}: aria-label = {aria!r}")
                time.sleep(3)

            browser.close()

        print("✅  Scrape complete")
        return {"items_inspected": value}

    except Exception as e:
        print("❌  Error:", e)
        raise HTTPException(status_code=500, detail=str(e))
