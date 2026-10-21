
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


# --- quiet logging ----------------------------------------------------------
# Lines are printed only when something changes: your bookings, the status of a
# slot, an error, a browser refresh. Scans where nothing changed print nothing.
# The word CLICKING is kept exactly as it was, because run_hourly.py looks for it.
REFRESH_MEMORY_STEP_MB = 25  # print a refresh line again only if memory moved this much

_last_selected = None    # last bookings list that was printed
_selected_ok = True      # False when the bookings table could not be read this scan
_last_slots = None       # slot -> (student, status) from the previous scan
_last_error = None       # first line of the error that is currently repeating
_error_repeats = 0
_pass_had_error = False
_refresh_announced = False
_last_refresh_mem = None


def print_selected(selected):
    """Print your bookings, but only when the list has changed."""
    global _last_selected
    if not _selected_ok:
        return  # the table could not be read: do not report a false change
    key = sorted((s["datetime"], s["email"], s["student"]) for s in selected)
    if key == _last_selected:
        return
    _last_selected = key
    if not selected:
        log("No consultations booked yet.")
        return
    log("=== CURRENT BOOKINGS ===")
    for s in sorted(selected, key=lambda x: x["datetime"]):
        log(f"{s['student']} | {s['email']} | {s['datetime']}")
    log("========================")


def report_slots(slots, quiet=()):
    """Print slots that are new, changed or gone since the previous scan.
    Slots in 'quiet' are recorded but not printed (the CLICKING line covers them)."""
    global _last_slots
    previous = _last_slots or {}
    for key, (student, status) in slots.items():
        if key in quiet:
            continue
        if previous.get(key, (None, None))[1] != status:
            log(f"{status}: {student} {key[0]} {key[1]}")
    for key, (student, _status) in previous.items():
        if key not in slots:
            log(f"No longer listed: {student} {key[0]} {key[1]}")
    if not slots and (_last_slots is None or _last_slots):
        log("No matching consultations right now.")
    _last_slots = slots


def _end_error_run():
    global _last_error, _error_repeats
    if _last_error is not None and _error_repeats:
        log(f"(that error repeated {_error_repeats} more times)")
    _last_error = None
    _error_repeats = 0


def log_error(msg):
    """Print an error once; identical repeats are counted, not printed."""
    global _last_error, _error_repeats, _pass_had_error
    _pass_had_error = True
    text = str(msg).strip()
    first = text.splitlines()[0] if text else "Error"
    if first == _last_error:
        _error_repeats += 1
        return
    _end_error_run()
    _last_error = first
    log(first)


def begin_pass():
    global _pass_had_error
    _pass_had_error = False


def pass_finished():
    """Call at the end of a loop pass; says so when a repeating error has stopped."""
    if not _pass_had_error and _last_error is not None:
        _end_error_run()
        log("Back to normal: no errors on the last scan.")


def announce_refresh(reloads, mem):
    """Print a browser-refresh line the first time, then only when memory has moved."""
    global _refresh_announced, _last_refresh_mem
    moved = (mem is not None and _last_refresh_mem is not None
             and abs(mem - _last_refresh_mem) >= REFRESH_MEMORY_STEP_MB)
    if _refresh_announced and not moved:
        return
    note = f", bot memory was {mem:.0f} MB" if mem is not None else ""
    if _refresh_announced:
        extra = ""
    elif mem is not None:
        extra = f". Later refreshes are silent unless memory moves by {REFRESH_MEMORY_STEP_MB} MB or more"
    else:
        extra = ". Later refreshes are silent (install psutil to see memory)"
    log(f"Fresh browser context started (memory reset) after {reloads} reloads{note}{extra}")
    _refresh_announced = True
    _last_refresh_mem = mem


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
    global _selected_ok
    _selected_ok = True
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
        _selected_ok = False
        log_error(f"Error reading selected consultations: {e}")

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


# print_selected() now lives in the "quiet logging" block under log() above.


def check_and_click(page):
    try:
        slots = {}  # this scan's view of every slot for your faculty (for change-only logging)

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

                    if week_counts.get(week_key, 0) >= 4:
                        slots[(email, dt)] = (student, "Skipped (weekly limit)")
                        break

                    if day_counts.get(day_key, 0) >= 3:
                        slots[(email, dt)] = (student, "Skipped (daily limit)")
                        break

                    checkbox = row.locator("input[type='checkbox']")
                    if checkbox.count() == 0:
                        slots[(email, dt)] = (student, "Skipped (no checkbox)")
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
        clicked_keys = set()

        for item in candidates:
            slots[(item["email"], item["datetime"])] = (
                item["student"], "Already selected" if item["checked"] else "Free slot")

        for item in candidates:
            dt = item["datetime"]

            if item["checked"]:
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
                slots[(item["email"], dt)] = (item["student"], "Skipped (overlap)")
                continue

            log(f"CLICKING: {item['student']} {item['email']} at {dt}")

            checkbox = item["row"].locator("input[type='checkbox']").first
            checkbox.scroll_into_view_if_needed()
            checkbox.click(force=True)

            clicked_any = True
            clicked_keys.add((item["email"], dt))

        report_slots(slots, quiet=clicked_keys)

        return clicked_any

    except Exception as e:
        log_error(f"Table processing error: {e}")
        return False


# --- memory fix (v2) --------------------------------------------------------
# What was measured: with context.route(...), Playwright's Python client keeps a
# Route and a Request object for EVERY sub-request of EVERY reload until the
# browser context is closed. On a page with many sub-requests that grows the
# bot's memory by roughly 100 MB a minute at this script's reload rate.
#   1. Images, fonts and CSS are now blocked inside the browser itself, so the
#      Python side never sees those requests.
#   2. A fresh browser context (login cookies carried over) is started every
#      RECYCLE_RELOADS reloads or RECYCLE_SECONDS, whichever comes first, but
#      never within NO_RECYCLE_AFTER_CLICK seconds of a tick.
# Nothing else in this script was changed.
import sys

RECYCLE_RELOADS = 100
RECYCLE_SECONDS = 120
NO_RECYCLE_AFTER_CLICK = 30  # never refresh right after a tick

BLOCKED_URLS = [
    "*.png*", "*.jpg*", "*.jpeg*", "*.gif*", "*.svg*", "*.webp*", "*.ico*",
    "*.css*", "*.woff*", "*.woff2*", "*.ttf*", "*.otf*",
]


def rss_mb():
    """This process's memory in MB, or None if psutil is not installed."""
    try:
        import psutil
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        return None


def open_page(browser, state=None):
    context = browser.new_context(storage_state=state) if state else browser.new_context()
    page = context.new_page()
    try:
        cdp = context.new_cdp_session(page)
        cdp.send("Network.enable")
        cdp.send("Network.setBlockedURLs", {"urls": BLOCKED_URLS})
    except Exception as e:
        log(f"Could not block images/CSS inside the browser ({e}); continuing without blocking")
    return context, page


def refresh_context(browser, context, page, reloads):
    """Close the current context and continue in a fresh one. Returns (context, page)."""
    mem = rss_mb()
    try:
        url = page.url
        state = context.storage_state()
        context.close()
        context, page = open_page(browser, state)
        page.goto(url, wait_until="domcontentloaded")
        announce_refresh(reloads, mem)
    except Exception as e:
        log(f"Context refresh failed ({e}); starting a clean context")
        try:
            context.close()
        except Exception:
            pass
        try:
            context, page = open_page(browser)
        except Exception as e2:
            log(f"Cannot open a new browser context ({e2}); exiting so a restart can recover")
            sys.exit(2)
    return context, page


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    context, page = open_page(browser)

    log("Bot started")

    last_recycle = time.time()
    last_click = 0.0
    reloads = 0

    while True:
        begin_pass()
        try:
            if not is_logged_in(page):
                login(page)

            page.reload(wait_until="domcontentloaded")
            reloads += 1
            page.wait_for_selector("text=Upcoming Consultations", timeout=60000)

            clicked = check_and_click(page)

            if clicked:
                last_click = time.time()
                time.sleep(3)
                page.reload(wait_until="commit")
                reloads += 1
                page.wait_for_selector("text=Consultations Selected", timeout=60000)

                selected = get_selected_consultations(page)
                print_selected(selected)

            now = time.time()
            if ((reloads >= RECYCLE_RELOADS or now - last_recycle >= RECYCLE_SECONDS)
                    and now - last_click >= NO_RECYCLE_AFTER_CLICK):
                context, page = refresh_context(browser, context, page, reloads)
                last_recycle = time.time()
                reloads = 0

            pass_finished()
            time.sleep(0.15)

        except Exception as e:
            log_error(f"Error: {str(e)}")
            time.sleep(2)

    browser.close()
