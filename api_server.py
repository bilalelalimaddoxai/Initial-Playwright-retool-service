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
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()

            # 1️⃣ Login
            print("🌐 Opening login page")
            page.goto("https://app.maddox.ai/login")
            page.fill("#login-email-input", creds.email)
            page.fill("#login-password-input", creds.password)
            time.sleep(1.5)

            for label in ("Login", "Anmelden"):
                btn = page.locator(f"button:has-text(\"{label}\")")
                if btn.is_visible(timeout=7_000):
                    btn.click(force=True)
                    print(f"✅ Clicked '{label}'")
                    break
            else:
                raise RuntimeError("Login button not found")

            # Wait for post-login UI
            print("⏳ Waiting after login")
            time.sleep(5)

            # 2️⃣ Click Monitor icon
            li_sel = "[data-testid='main-menu-monitor']"
            a_sel = "[data-testid='main-menu-monitor'] a"

            li = page.locator(li_sel)
            li.wait_for(state="attached", timeout=40_000)
            li.scroll_into_view_if_needed()
            li.hover()
            time.sleep(0.3)

            if page.locator(a_sel).count() > 0:
                anchor = page.locator(a_sel)
                try:
                    anchor.click(force=True, timeout=3_000)
                    print("✅ Anchor click fired")
                except:
                    print("⚠️ Anchor click timed-out → JS click fallback")
                    page.evaluate("el => el.click()", anchor)
            else:
                print("⚠️ No <a> child → JS click <li>")
                page.evaluate("el => el.click()", li)

            # 3️⃣ Wait for Monitor view
            print("⏳ Waiting for /monitor navigation")
            page.wait_for_url("**/monitor**", timeout=60_000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            print("✅ Monitor page loaded")

            # 4️⃣ Extract KPI
            span = page.locator(
                "div:has(h5:text-is('Items inspected')) "
                "span[aria-label*='items inspected']"
            )
            value = "(not available)"
            for _ in range(3):
                span.wait_for(state="attached", timeout=7_000)
                aria = span.get_attribute("aria-label") or ""
                if aria and aria.strip()[0].isdigit():
                    value = aria.split()[0]
                    break
                time.sleep(3)

            # Debugging output
            page.screenshot(path="/tmp/monitor_debug.png")
            with open("/tmp/monitor_debug.html", "w", encoding="utf-8") as f:
                f.write(page.content())

            browser.close()

        print(f"📊 Items inspected = {value}")
        return {"items_inspected": value}

    except Exception as e:
        print("❌ Final error:", e)
        raise HTTPException(status_code=500, detail=str(e))
