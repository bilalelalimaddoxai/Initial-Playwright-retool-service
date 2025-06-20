from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import time
import os

app = FastAPI()

class Credentials(BaseModel):
    email: str
    password: str

@app.post("/scrape/items-inspected")
def scrape_items_inspected(creds: Credentials):
    try:
        print("🔓 Starting scraper")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Step 1: Open login page
            page.goto("https://app.maddox.ai/login")

            # Step 2: Fill in credentials
            page.fill("#login-email-input", creds.email)
            page.fill("#login-password-input", creds.password)
            time.sleep(1.5)

            # Step 3: Try both button labels
            login_clicked = False
            for label in ["Login", "Anmelden"]:
                try:
                    print(f"🔍 Trying button with text: {label}")
                    login_button = page.locator(f"button:has-text('{label}')")
                    login_button.wait_for(state="visible", timeout=5000)
                    login_button.click(force=True)
                    print(f"✅ Clicked '{label}' button")
                    login_clicked = True
                    break
                except Exception as e:
                    print(f"❌ Failed to click '{label}':", e)

            if not login_clicked:
                raise RuntimeError("Login button not found in either language.")

            # Step 4: Wait for sidebar and click Monitor
            time.sleep(2)
            try:
                monitor_button = page.locator('[data-testid="main-menu-Monitor"]')
                monitor_button.wait_for(state="visible", timeout=7000)
                monitor_button.click()
                print("✅ Clicked Monitor button in sidebar.")
            except Exception as e:
                print("❌ Could not click Monitor menu item:", e)
                page.screenshot(path="/tmp/sidebar_debug.png")
                with open("/tmp/sidebar_debug.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                raise HTTPException(status_code=500, detail="Sidebar not found or not clickable.")

            # Step 5: Extract KPI
            try:
                span = page.locator(
                    "div:has(h5:text-is('Items inspected')) span[aria-label*='items inspected']"
                )
                value = "(not available)"
                for attempt in range(3):
                    span.wait_for(timeout=5000)
                    aria = span.get_attribute("aria-label") or ""
                    if aria.strip() and aria.strip()[0].isdigit():
                        value = aria.split()[0]
                        break
                    else:
                        print(f"⏳ Attempt {attempt+1}: KPI not ready — aria-label = {aria!r}")
                        time.sleep(3)

                print(f"📊 Items inspected: {value}")
                page.screenshot(path="/tmp/monitor_debug.png")
                with open("/tmp/monitor_debug.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                browser.close()
                return {"items_inspected": value}

            except Exception as e:
                print("❌ Failed to extract KPI:", e)
                raise HTTPException(status_code=500, detail="Failed to extract KPI.")

    except Exception as e:
        print("❌ Final error:", e)
        raise HTTPException(status_code=500, detail=str(e))


# Debug file download routes
@app.get("/debug/sidebar-html")
def get_sidebar_html():
    path = "/tmp/sidebar_debug.html"
    if os.path.exists(path):
        return FileResponse(path, media_type="text/html", filename="sidebar_debug.html")
    raise HTTPException(status_code=404, detail="Sidebar HTML debug file not found")

@app.get("/debug/sidebar-screenshot")
def get_sidebar_screenshot():
    path = "/tmp/sidebar_debug.png"
    if os.path.exists(path):
        return FileResponse(path, media_type="image/png", filename="sidebar_debug.png")
    raise HTTPException(status_code=404, detail="Sidebar screenshot not found")

@app.get("/debug/monitor-html")
def get_monitor_html():
    path = "/tmp/monitor_debug.html"
    if os.path.exists(path):
        return FileResponse(path, media_type="text/html", filename="monitor_debug.html")
    raise HTTPException(status_code=404, detail="Monitor HTML debug file not found")

@app.get("/debug/monitor-screenshot")
def get_monitor_screenshot():
    path = "/tmp/monitor_debug.png"
    if os.path.exists(path):
        return FileResponse(path, media_type="image/png", filename="monitor_debug.png")
    raise HTTPException(status_code=404, detail="Monitor screenshot not found")

