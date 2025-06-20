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
    1. Log in to Maddox.ai        (Login / Anmelden button)
    2. Read the <a href="/monitor?..."> inside the sidebar (no clicking)
    3. page.goto() that URL directly
    4. Extract the “Items inspected” KPI
    """

    try:
        print("🔓  Starting scraper")
        with sync_playwright() as pw:
            browser = pw.chromium.launch()                 # headless on Render
            page = browser.new_page()

            # ─── 1) LOGIN ───────────────────────────────────────────────
            page.goto("https://app.maddox.ai/login")
            page.fill("#login-email-input", creds.email)
            page.fill("#login-password-input", creds.password)
            time.sleep(1.5)

            for label in ("Login", "Anmelden"):
                btn = page.locator(f"button:has-text('{label}')")
                if btn.is_visible(timeout=7_000):
                    btn.click(force=True)
                    print(f"✅  Clicked '{label}' button")
                    break
            else:
                raise RuntimeError("Login button not found")

            # ─── 2) GET MONITOR LINK & NAVIGATE ────────────────────────
            time.sleep(3)   # give React time for the sidebar
            link_href = page.locator("[data-testid='main-menu-monitor'] a").get_attribute("href")
            if not link_href:
                link_href = "/monitor"                      # fallback
            full_url = "https://app.maddox.ai" + link_href
            print(f"➡️  goto {full_url}")
            page.goto(full_url, wait_until="networkidle")
            time.sleep(2)
            print("✅  Monitor loaded")

            # ─── 3) EXTRACT KPI ────────────────────────────────────────
            span = page.locator(
                "div:has(h5:text-is('Items inspected')) span[aria-label*='items inspected']"
            )
            value = "(not available)"
            for _ in range(3):
                span.wait_for(state="attached", timeout=7_000)
                aria = span.get_attribute("aria-label") or ""
                if aria.strip() and aria[0].isdigit():
                    value = aria.split()[0]
                    break
                time.sleep(3)

            browser.close()

        print(f"📊  Items inspected = {value}")
        return {"items_inspected": value}

    except Exception as e:
        print("❌  Error:", e)
        raise HTTPException(status_code=500, detail=str(e))
