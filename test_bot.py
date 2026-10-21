from playwright.sync_api import sync_playwright
import time
from datetime import datetime

ROLLNO = "251280070003"
PASSWORD = "07/08/2000"
LOGIN_TEXT = "Hello YOGI RANCHHOD PATEL"
URL = "https://portal.manipal.edu/statistics/I11"

priority_order = [
    "suresha.kharvi@manipal.edu",
    "satya.narayana@manipal.edu",
    "vasudev.guddattu@manipal.edu"
]

# ---------------- EMAIL (DISABLED) ----------------
"""
import smtplib
from email.mime.text import MIMEText

def send_email(message):
    sender = "your_email@gmail.com"
    password = "your_app_password"

    msg = MIMEText(message)
    msg["Subject"] = "Consultation Booked"
    msg["From"] = sender
    msg["To"] = sender

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)
"""
# ------------------------------------------------


def login(page):
    page.goto(URL)

    page.select_option("select", value="S")
    page.get_by_role("button", name="CONTINUE").click()

    page.wait_for_selector("input[type='password']")

    page.locator("input[type='text']").first.fill(ROLLNO)
    page.locator("input[type='password']").fill(PASSWORD)

    page.get_by_role("button", name="LOGIN").click()

    page.wait_for_load_state("networkidle")

    page.get_by_role("link", name="CONSULTATION DETAILS").click()
    page.wait_for_load_state("networkidle")


def is_logged_in(page):
    try:
        return page.get_by_text(LOGIN_TEXT).count() > 0
    except:
        return False


def parse_datetime(date_str, time_str):
    try:
        return datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
    except:
        return None


def times_overlap(t1, t2, buffer_minutes=30):
    if not t1 or not t2:
        return False
    return abs((t1 - t2).total_seconds()) < buffer_minutes * 60


def check_selected_table(page):
    try:
        section = page.locator("text=Consultations Selected").locator("..")
        table = section.locator("table")

        rows = table.locator("tr")
        row_count = rows.count()

        print("\n--- SELECTED CONSULTATIONS ---")

        for i in range(row_count):
            row = rows.nth(i)
            cells = row.locator("td")

            if cells.count() == 0:
                continue

            values = [cells.nth(j).inner_text().strip() for j in range(cells.count())]

            try:
                email = values[10]
                date = values[8]
                time_val = values[9]
            except:
                continue

            print(f"{email} | {date} {time_val}")

        print("--- END ---\n")

    except Exception as e:
        print("Error reading selected table:", e)


def check_and_click(page):
    try:
        section = page.locator("text=Upcoming Consultations").locator("..")
        table = section.locator("table")

        rows = table.locator("tr")
        row_count = rows.count()

        candidates = []

        for i in range(row_count):
            row = rows.nth(i)
            cells = row.locator("td")

            if cells.count() == 0:
                continue

            row_text = row.inner_text().lower()

            for email in priority_order:
                if email in row_text:

                    cell_values = [cells.nth(j).inner_text().strip() for j in range(cells.count())]

                    try:
                        date = cell_values[8]
                        time_val = cell_values[9]
                    except:
                        continue

                    dt = parse_datetime(date, time_val)

                    checkbox = row.locator("input[type='checkbox']")
                    if checkbox.count() == 0:
                        continue

                    is_checked = checkbox.first.is_checked()

                    candidates.append({
                        "row": row,
                        "email": email,
                        "datetime": dt,
                        "checked": is_checked,
                        "priority": priority_order.index(email)
                    })

        candidates.sort(key=lambda x: x["priority"])

        selected_times = []
        clicked_any = False

        for item in candidates:
            email = item["email"]
            dt = item["datetime"]
            checked = item["checked"]
            checkbox = item["row"].locator("input[type='checkbox']").first

            if checked:
                selected_times.append(dt)
                continue

            overlap = any(times_overlap(dt, t) for t in selected_times)

            if overlap:
                continue

            print(f"Clicking {email} at {dt}")
            checkbox.click()

            selected_times.append(dt)
            clicked_any = True

        return clicked_any

    except Exception as e:
        print("Error in table logic:", e)
        return False


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    just_logged_in = False

    while True:
        try:
            if not is_logged_in(page):
                print("Not logged in. Logging in...")
                login(page)
                print("Login successful.")
                just_logged_in = True

            else:
                print("Session active. Refreshing...")

                page.reload(wait_until="domcontentloaded")
                page.wait_for_selector("text=Upcoming Consultations")

                print("Checked at:", time.strftime("%H:%M:%S"))

                clicked = check_and_click(page)

                if clicked:
                    print("Clicked. Waiting 20 seconds...")
                    time.sleep(20)

                    page.reload(wait_until="domcontentloaded")
                    page.wait_for_selector("text=Consultations Selected")

                    check_selected_table(page)

                    # send_email("Consultation booked")

                just_logged_in = False

            if not just_logged_in:
                time.sleep(3)

        except Exception as e:
            print("Error:", e)
            time.sleep(5)

    browser.close()