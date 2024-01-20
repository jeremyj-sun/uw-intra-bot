from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from datetime import datetime
import os


def login_to_intramural_site(browser):
    page = browser.new_page()
    page.goto("https://warrior.uwaterloo.ca/")
    page.wait_for_timeout(1000)

    # Execute the JavaScript code associated with the site's sign in button
    # Not an actual button; function name may change in the future
    page.evaluate("showLogin('/')")

    watiam_login_button = 'button[title="WATIAM USERS"]'  # WATIAM login
    page.wait_for_selector(f"{watiam_login_button}:visible")
    page.click(watiam_login_button)
    page.wait_for_timeout(1000)

    # WATIAM login redirects to Microsoft. Login to Microsoft account.
    microsoft_email_identifier = 'input[type="email"]'
    page.wait_for_selector(microsoft_email_identifier)
    page.fill(microsoft_email_identifier, os.getenv("EMAIL"))
    page.press(microsoft_email_identifier, "Enter")

    microsoft_password_identifier = 'input[type="password"]'
    page.wait_for_selector(microsoft_password_identifier)
    page.fill(microsoft_password_identifier, os.getenv("PASSWORD"))
    page.press(microsoft_password_identifier, "Enter")

    return page


def fetch_game_data(page, team_id):
    class GameData:
        def __init__(self, time, location, team1, team2):
            self.time = time
            self.location = location
            self.team1 = team1
            self.team2 = team2

    def convert_to_iso(date_str):
        # Assume date input is: Sunday, January 21, 2024 @ 4:00 PM
        # Remove the day of the week and '@' to output yyyy-mm-ddThh:mm:ss
        clean_date = " ".join(date_str.split()[1:]).replace("@", "")
        return datetime.strptime(clean_date, "%B %d, %Y %I:%M %p").isoformat()

    data_url = f"https://warrior.uwaterloo.ca/team/getteaminfo?teamid={team_id}"
    page.goto(data_url)
    soup = BeautifulSoup(page.content(), "html.parser")

    # Only time and locations are in class="game-card_title".
    # Only team names are in class="game-card-team-name".
    # These may change in the future. Either other data are included or a name change
    time_and_locations = [
        e.get_text(strip=True) for e in soup.find_all(class_="game-card-title")
    ]
    team_names = [
        e.get_text(strip=True) for e in soup.find_all(class_="game-card-team-name")
    ]

    # Since each data is separate in their own div, we ASSUME that each
    # relevant data is next to and after each other. See example:
    # arr1 := time1, place1, time2, place2, time3, place3, ...
    # arr2 := team1,  team1, team2,  team2, team3,  team3, ...
    game_data = [
        GameData(convert_to_iso(time), location, team1, team2)
        for (time, location), (team1, team2) in zip(
            zip(time_and_locations[::2], time_and_locations[1::2]),
            zip(team_names[::2], team_names[1::2]),
        )
    ]

    return game_data


def main():
    with sync_playwright() as playwright:
        # Sensitive folder containing browser data. Keep it secure.
        persistant_user_data_dir = "./browser/"

        if not os.path.exists(persistant_user_data_dir):
            os.makedirs(persistant_user_data_dir)

        # Persistant data is to keep browser recognized by Microsoft login,
        # so it does not require 2-factor authentication every time. May still ask
        # it sometimes because of forced logouts (mandated by organizations)
        browser = playwright.chromium.launch_persistent_context(
            persistant_user_data_dir, headless=False
        )

        load_dotenv()

        logged_in_page = login_to_intramural_site(browser)

        # Wait at least 3 seconds. Will not fetch the data in 1 second.
        # Will only get the home sign in page HTML otherwise
        logged_in_page.wait_for_timeout(6000)
        game_data = fetch_game_data(logged_in_page, os.getenv("TEAM_ID"))

        browser.close()

        return game_data


if __name__ == "__main__":
    main()
