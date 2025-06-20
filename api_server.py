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

            # ─── Step 4: Click the Monitor icon (works collapsed & headless) ─────────────
            print("⏳  Waiting for sidebar")
            time.sleep(3)                         # give React time in Render
            
            # we’ll click the <a> child if present, else the <li>
            selector_li = "[data-testid='main-menu-monitor']"
            selector_a  = "[data-testid='main-menu-monitor'] a"
            
            # 1) wait until the <li> exists in the DOM
            monitor_li = page.locator(selector_li)
            monitor_li.wait_for(state="attached", timeout=20_000)
            
            # 2) if <a> exists, scroll & JS-click it; else click the <li>
            if page.locator(selector_a).count() > 0:
                monitor_a = page.locator(selector_a)
                monitor_a.scroll_into_view_if_needed()
                page.evaluate("el => el.click()", monitor_a)
            else:
                monitor_li.scroll_into_view_if_needed()
                page.evaluate("el => el.click()", monitor_li)
            
            print("✅  Fired JS click on Monitor")
            
            # 3) wait for navigation
            page.wait_for_url("**/monitor**", timeout=15_000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            print("✅  Monitor page loaded")


            browser.close()

        print("✅  Scrape complete")
        return {"items_inspected": value}

    except Exception as e:
        print("❌  Error:", e)
        raise HTTPException(status_code=500, detail=str(e))
