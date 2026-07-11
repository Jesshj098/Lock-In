"""
LOCK IN - v2 (macOS version)
Programming Final Project
Author: Jesse Velazquez Rojas
Data and AI Engineering - 2nd Quadrimester (May-August 2026)

Lock In is a small productivity assistant. The user enters a study
goal and a focus time (in minutes). While the timer is running, the
program checks the app/window that is currently active on screen
every 5 seconds. If that app or window belongs to a "distraction"
app (the ones listed in blacklist.json), the program shows a
reminder on the console and counts it as a distraction. When the
timer is over, a summary of the session is printed.

This version uses macOS's built-in "osascript" (AppleScript) through
the subprocess module to ask the operating system which app is in
front, instead of win32gui/win32process (those only exist on
Windows). Everything else (JSON, logging, timer, error handling)
works the same way.

This is a school project, so the code is kept simple on purpose:
no classes, no OOP, just variables, functions, loops, if statements,
dictionaries, JSON and basic error handling, like we have seen in
class so far.

IMPORTANT (macOS only): the first time you run this, macOS will ask
you to give your Terminal (or VS Code) permission under
System Settings > Privacy & Security > Accessibility, so it can
"see" which app/window is active. If you don't grant it, the app
detection will fail and the program will log the error and keep
using "Unknown" as the app name.
"""

# =========================================================
# IMPORTS
# =========================================================

import json
import time
import logging
import os
import subprocess


# =========================================================
# LOGGING CONFIGURATION
# =========================================================
# The professor asked us to create a /logs folder with a log file
# that is generated automatically by the program (not by hand).
# So first we make sure the folder exists, and then we tell the
# logging module to write everything there.

LOGS_FOLDER = "logs"
LOG_FILE_PATH = os.path.join(LOGS_FOLDER, "app.log")

# os.makedirs with exist_ok=True will create the folder only if it
# is missing, if it already exists it will not raise an error.
if not os.path.exists(LOGS_FOLDER):
    os.makedirs(LOGS_FOLDER, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE_PATH,
    level=logging.INFO,
    format="%(asctime)s — [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# We log that the program started as soon as the logging is ready.
logging.info("Program started.")


# =========================================================
# FUNCTIONS
# =========================================================

def load_blacklist(file_name="blacklist.json"):
    """
    Reads the blacklist.json file and returns the list of apps
    that count as a distraction. If something goes wrong (file
    missing, bad JSON, etc.) we log the problem and return a
    small default list so the program can keep running.
    """
    default_apps = ["TikTok", "Instagram", "Facebook", "Discord", "YouTube"]

    try:
        with open(file_name, "r", encoding="utf-8") as file:
            data = json.load(file)
            apps = data.get("apps", [])

            if len(apps) == 0:
                logging.warning("blacklist.json was loaded but the 'apps' list is empty.")
            else:
                logging.info("Blacklist loaded successfully (" + str(len(apps)) + " apps).")

            return apps

    except FileNotFoundError:
        logging.error("blacklist.json was not found. Using the default blacklist instead.")
        print("Could not find blacklist.json, using a default list of apps.")
        return default_apps

    except json.JSONDecodeError:
        logging.error("blacklist.json has invalid JSON format. Using the default blacklist instead.")
        print("blacklist.json looks broken (invalid JSON), using a default list of apps.")
        return default_apps

    except Exception as error:
        # This is a "catch all" in case something we did not think
        # of happens, so the program does not crash.
        logging.error("Unexpected error while loading blacklist.json: " + str(error))
        print("Something went wrong loading the blacklist, using a default list.")
        return default_apps


def ask_study_goal():
    """
    Asks the user what they want to study. Keeps asking until the
    user types something that is not empty.
    """
    goal = ""
    while goal.strip() == "":
        goal = input("What is your study goal? ")
        if goal.strip() == "":
            print("Please type something, the goal cannot be empty.")
            logging.warning("Invalid input: study goal was left empty.")

    logging.info("Study goal set to: " + goal)
    return goal


def ask_focus_time():
    """
    Asks the user how many minutes they want to focus for. Uses a
    try/except to catch the case where the user does not type a
    number, and keeps asking until a valid positive number is given.
    """
    while True:
        user_input = input("How many minutes do you want to focus? ")

        try:
            minutes = int(user_input)

            if minutes <= 0:
                print("The focus time has to be a positive number.")
                logging.warning("Invalid input: focus time was not positive (" + user_input + ").")
                continue

            logging.info("Focus time set to " + str(minutes) + " minutes.")
            return minutes

        except ValueError:
            print("That is not a valid number, try again (example: 25).")
            logging.warning("Invalid input: focus time was not a number (" + user_input + ").")


def run_applescript(script_text):
    """
    Small helper function that runs a piece of AppleScript using
    "osascript" (a command that comes built into every Mac) and
    returns the text it prints back, without the extra newline at
    the end. If the command fails for any reason, it raises an
    exception so the caller can handle it with try/except.
    """
    result = subprocess.run(
        ["osascript", "-e", script_text],
        capture_output=True,
        text=True,
        timeout=5
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def get_active_window_info():
    """
    Uses AppleScript (through osascript) to find out which app is
    currently in front (the active/frontmost app), and if that app
    is a browser (Safari or Google Chrome), it also tries to read
    the title of the current tab, since a lot of "distraction apps"
    like TikTok or Instagram are actually websites opened in a
    browser, not separate apps.

    Returns a tuple: (window_title, process_name)
    If something fails, returns ("Unknown", "Unknown") and logs
    the error, so the main loop does not crash.
    """
    try:
        # Ask macOS which app is currently in front.
        app_name = run_applescript(
            'tell application "System Events" to get name of first process whose frontmost is true'
        )

        window_title = app_name

        # If the active app is a browser, try to get the tab title
        # too, because that is where "TikTok", "Instagram", etc.
        # usually show up.
        if app_name == "Safari":
            try:
                window_title = run_applescript(
                    'tell application "Safari" to get name of front document'
                )
            except Exception as error:
                logging.warning("Could not read the Safari tab title: " + str(error))

        elif app_name == "Google Chrome":
            try:
                window_title = run_applescript(
                    'tell application "Google Chrome" to get title of active tab of front window'
                )
            except Exception as error:
                logging.warning("Could not read the Google Chrome tab title: " + str(error))

        return window_title, app_name

    except Exception as error:
        logging.error("Could not detect the active window/app: " + str(error))
        return "Unknown", "Unknown"


def is_distraction(window_title, process_name, blacklist):
    """
    Checks if the window title or the process name contains any of
    the words in the blacklist. Everything is compared in lowercase
    so it does not matter if the user wrote "tiktok" or "TikTok" in
    blacklist.json.
    """
    title_lower = window_title.lower()
    process_lower = process_name.lower()

    for app in blacklist:
        app_lower = app.lower()
        if app_lower in title_lower or app_lower in process_lower:
            return True

    return False


def show_reminder(study_goal, distracting_app):
    """
    Prints a reminder message to the console and logs the event.
    """
    message = "REMINDER: Stop scrolling! Get back to your goal -> " + study_goal
    print("\n*** " + message + " (detected: " + distracting_app + ") ***\n")
    logging.warning("Distraction detected (" + distracting_app + "). Reminder displayed to the user.")


def calculate_performance(distraction_count):
    """
    Returns a text with the performance rating, based on the rules
    given in the assignment:
        0 distractions -> Excellent
        1-2 distractions -> Good
        3+ distractions -> Needs Improvement
    """
    if distraction_count == 0:
        return "Excellent"
    elif distraction_count <= 2:
        return "Good"
    else:
        return "Needs Improvement"


def show_summary(study_goal, focus_time, distraction_count):
    """
    Prints the final summary of the session and also logs it, so
    there is a record of every session that was run.
    """
    performance = calculate_performance(distraction_count)

    print("\n===================================")
    print("           SESSION SUMMARY")
    print("===================================")
    print("Goal:         " + study_goal)
    print("Focus time:   " + str(focus_time) + " minutes")
    print("Distractions: " + str(distraction_count))
    print("Performance:  " + performance)
    print("===================================\n")

    logging.info(
        "Session finished. Goal: '" + study_goal + "' | Time: " + str(focus_time) +
        " min | Distractions: " + str(distraction_count) + " | Performance: " + performance
    )


# =========================================================
# MAIN PROGRAM
# =========================================================

def main():
    print("=====================================")
    print("             LOCK IN")
    print("     Your simple study assistant")
    print("=====================================\n")

    # Load the blacklist of distracting apps from the JSON file.
    blacklist = load_blacklist()

    # Ask the user for the basic session info.
    study_goal = ask_study_goal()
    focus_time = ask_focus_time()

    print("\nStarting focus session for " + str(focus_time) + " minutes...")
    print("Checking the active window every 5 seconds. Do not close this window.\n")

    logging.info("Focus session started.")

    # CHECK_INTERVAL is how often (in seconds) we look at the active
    # window. total_seconds is how long the whole session will last.
    check_interval = 5
    total_seconds = focus_time * 60

    distraction_count = 0
    seconds_passed = 0
    start_time = time.time()

    # Main loop: it keeps running until the focus time is over.
    try:
        while seconds_passed < total_seconds:
            time.sleep(check_interval)
            seconds_passed = time.time() - start_time

            window_title, process_name = get_active_window_info()
            logging.info("Active window detected -> title: '" + window_title + "' | process: '" + process_name + "'")

            if is_distraction(window_title, process_name, blacklist):
                distraction_count = distraction_count + 1
                show_reminder(study_goal, window_title if window_title else process_name)
            else:
                print("Still focused on: " + study_goal + " (time left: " +
                      str(int((total_seconds - seconds_passed) // 60)) + " min)")

    except KeyboardInterrupt:
        # In case the student stops the program early with Ctrl+C,
        # we still want to show a summary and log that it happened.
        print("\nSession interrupted by the user.")
        logging.warning("Focus session was interrupted manually by the user (Ctrl+C).")

    except Exception as error:
        # Any other unexpected error during the monitoring loop.
        print("An unexpected error happened during the session: " + str(error))
        logging.error("Unexpected error during the focus session: " + str(error))

    finally:
        logging.info("Focus session ended.")
        show_summary(study_goal, focus_time, distraction_count)

    logging.info("Program closed.")


# This makes sure main() only runs when we execute this file
# directly, and not if it is ever imported from another file.
if __name__ == "__main__":
    main()
