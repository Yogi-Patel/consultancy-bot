
from playwright.sync_api import sync_playwright
import time
from datetime import datetime
import os 


ROLLNO = "251280070003"
PASSWORD = "07/08/2000"
LOGIN_TEXT = "Hello YOGI RANCHHOD PATEL"

#ROLLNO = "251280070003"
#PASSWORD = "07/08/2000"
#LOGIN_TEXT = "Hello YOGI RANCHHOD PATEL"

URL = "https://portal.manipal.edu/statistics/I11"

priority_order = [
    "suresha.kharvi@manipal.edu",
    "bhagyajyothi.rao@manipal.edu",
    "satya.narayana@manipal.edu",
    "vasudev.guddattu@manipal.edu",
    "varunsg.kumar@manipal.edu"
]


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def login(page):
    log("Logging in...")

    page.goto(URL, timeout=60000)

    page.select_option("select", value="S")
    page.get_by_role("button", name="CONTINUE").click()

    page.wait_for_selector("input[type='password']", timeout=60000)

    page.locator("input[type='text']").first.fill(ROLLNO)
    page.locator("input[type='password']").fill(PASSWORD)

    page.get_by_role("button", name="LOGIN").click()
    page.wait_for_load_state("networkidle")

    page.get_by_role("link", name="CONSULTATION DETAILS").click()
    page.wait_for_load_state("networkidle")

    log("Login successful")


def is_logged_in(page):
    try:
        return page.get_by_text(LOGIN_TEXT).count() > 0
    except:
        return False


def parse_datetime(date_str, time_str):
    try:
        return datetime.strptime(f"{date_str.strip()} {time_str.strip()}", "%d/%m/%Y %H:%M")
    except:
        return None


def times_overlap(t1, t2):
    if not t1 or not t2:
        return False
    return abs((t1 - t2).total_seconds()) < 1800


def get_selected_consultations(page):
    results = []
    try:
        table = page.locator("table").last
        rows = table.locator("tr")

        for i in range(rows.count()):
            row = rows.nth(i)
            cells = row.locator("td")

            if cells.count() == 0:
                continue

            values = [cells.nth(j).inner_text().strip() for j in range(cells.count())]

            try:
                student = values[1].upper()
                date = values[7]
                time_val = values[8]
                email = values[9]

                dt = parse_datetime(date, time_val)

                if dt:
                    results.append({
                        "email": email,
                        "datetime": dt,
                        "student": student
                    })
            except:
                continue

    except Exception as e:
        log(f"Error reading selected consultations: {e}")

    return results


def count_weekly_consultations(selected):
    week_counts = {}
    for item in selected:
        key = item["datetime"].isocalendar()[:2]
        week_counts[key] = week_counts.get(key, 0) + 1
    return week_counts


def count_daily_consultations(selected):
    day_counts = {}
    for item in selected:
        key = item["datetime"].date()
        day_counts[key] = day_counts.get(key, 0) + 1
    return day_counts


def print_selected(selected):
    if not selected:
        log("No consultations booked yet.")
        return

    log("=== CURRENT BOOKINGS ===")
    for s in selected:
        log(f"{s['student']} | {s['email']} | {s['datetime']}")
    log("========================")


def check_and_click(page):
    try:
        log("Scanning upcoming consultations...")

        selected = get_selected_consultations(page)
        print_selected(selected)

        week_counts = count_weekly_consultations(selected)
        day_counts = count_daily_consultations(selected)

        section = page.locator("text=Upcoming Consultations").locator("..")
        table = section.locator("table")
        rows = table.locator("tr")

        candidates = []

        for i in range(rows.count()):
            row = rows.nth(i)
            cells = row.locator("td")

            if cells.count() == 0:
                continue

            row_text = row.inner_text().lower()

            for email in priority_order:
                if email in row_text:
                    values = [cells.nth(j).inner_text().strip() for j in range(cells.count())]

                    try:
                        student = values[1].upper()
                        date = values[8]
                        time_val = values[9]
                    except:
                        continue

                    dt = parse_datetime(date, time_val)
                    if not dt:
                        continue

                    week_key = dt.isocalendar()[:2]
                    day_key = dt.date()

                    if week_counts.get(week_key, 0) >= 2:
                        log(f"Skipped (weekly limit): {student} {email} {dt}")
                        break

                    if day_counts.get(day_key, 0) >= 2:
                        log(f"Skipped (daily limit): {student} {email} {dt}")
                        break

                    checkbox = row.locator("input[type='checkbox']")
                    if checkbox.count() == 0:
                        break

                    candidates.append({
                        "row": row,
                        "email": email,
                        "datetime": dt,
                        "student": student,
                        "checked": checkbox.first.is_checked(),
                        "priority": priority_order.index(email)
                    })

                    break

        candidates.sort(key=lambda x: (x["priority"], x["datetime"]))

        selected_slots = [(item["datetime"], item["email"]) for item in selected]

        clicked_any = False

        for item in candidates:
            dt = item["datetime"]

            if item["checked"]:
                log(f"Already selected: {item['student']} {item['email']} {dt}")
                selected_slots.append((dt, item["email"]))
                continue

            conflict = False

            for existing_dt, existing_email in selected_slots:
                if existing_email == item["email"]:
                    continue

                if times_overlap(dt, existing_dt):
                    conflict = True
                    break

            if conflict:
                log(f"Skipped (overlap): {item['student']} {item['email']} {dt}")
                continue

            log(f"CLICKING: {item['student']} {item['email']} at {dt}")

            checkbox = item["row"].locator("input[type='checkbox']").first
            checkbox.scroll_into_view_if_needed()
            checkbox.click(force=True)

            clicked_any = True

        if not candidates:
            log("No matching consultations found")

        return clicked_any

    except Exception as e:
        log(f"Table processing error: {e}")
        return False


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    context = browser.new_context()

    context.route("**/*", lambda route: (
        route.abort() if route.request.resource_type in ["image", "font", "stylesheet"]
        else route.continue_()
    ))

    page = context.new_page()

    log("Bot started")

    counter = 0
    while True:
        try:
            counter += 1 

            if counter % 500 == 0:
                os.system("cls")

            if not is_logged_in(page):
                login(page)

            page.reload(wait_until="domcontentloaded")
            page.wait_for_selector("text=Upcoming Consultations", timeout=60000)

            clicked = check_and_click(page)

            if clicked:
                time.sleep(3)
                page.reload(wait_until="commit")
                page.wait_for_selector("text=Consultations Selected", timeout=60000)

                selected = get_selected_consultations(page)
                print_selected(selected)

            time.sleep(0.15)

        except Exception as e:
            log(f"Error: {str(e)}")
            time.sleep(2)

    browser.close()