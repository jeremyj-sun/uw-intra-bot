from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from game_data import GameData

from datetime import datetime
import pytz
import os

# DEBUG flag will enable headed mode, which is helpful for troubleshooting MFA
DEBUG = True

async def login_to_intramural_site(browser):
    page = await browser.new_page()
    await page.goto("https://warrior.uwaterloo.ca/")
    await page.wait_for_timeout(1000)

    # Execute the JavaScript code associated with the site's sign in button
    # Not an actual button; function name may change in the future
    await page.evaluate("showLogin('/')")

    watiam_login_button = 'button[title="WATIAM USERS"]'  # WATIAM login
    await page.wait_for_selector(f"{watiam_login_button}:visible")
    await page.click(watiam_login_button)
    await page.wait_for_timeout(1000)

    # WATIAM login redirects to Microsoft. Login to Microsoft account.
    microsoft_email_identifier = 'input[type="email"]'
    await page.wait_for_selector(microsoft_email_identifier)
    await page.fill(microsoft_email_identifier, os.getenv("EMAIL"))
    await page.press(microsoft_email_identifier, "Enter")

    microsoft_password_identifier = 'input[type="password"]'
    await page.wait_for_selector(microsoft_password_identifier)
    await page.fill(microsoft_password_identifier, os.getenv("PASSWORD"))
    await page.press(microsoft_password_identifier, "Enter")

    return page


async def fetch_game_data_helper(page, team_id):
    def convert_to_iso(date_str):
        # Assume date input is: Sunday, January 21, 2024 @ 4:00 PM
        # Remove the day of the week and '@' to output yyyy-mm-ddThh:mm:ss
        clean_date = " ".join(date_str.split()[1:]).replace("@", "")
        tz = pytz.timezone('America/Toronto')
        localized_date = tz.localize(datetime.strptime(clean_date, "%B %d, %Y %I:%M %p"))
        return localized_date.isoformat()

    data_url = f"https://warrior.uwaterloo.ca/team/getteaminfo?teamid={team_id}"
    await page.goto(data_url)
    soup = BeautifulSoup(await page.content(), "html.parser")

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


async def fetch_game_data():
    async with async_playwright() as playwright:
        # Sensitive folder containing browser data. Keep it secure.
        persistant_user_data_dir = "./browser/"

        if not os.path.exists(persistant_user_data_dir):
            os.makedirs(persistant_user_data_dir)

        # Persistant data is to keep browser recognized by Microsoft login,
        # so it does not require 2-factor authentication every time. May still ask
        # it sometimes because of forced logouts (mandated by organizations)
        if DEBUG:
            browser = await playwright.chromium.launch_persistent_context(persistant_user_data_dir, headless=False, slow_mo=100)
        else:
            browser = await playwright.chromium.launch_persistent_context(persistant_user_data_dir)

        load_dotenv()

        logged_in_page = await login_to_intramural_site(browser)

        # Wait at least 3 seconds. Will not fetch the data in 1 second.
        # Will only get the home sign in page HTML otherwise
        await logged_in_page.wait_for_timeout(int(os.getenv('TIMEOUT_MS')))
        game_data = await fetch_game_data_helper(logged_in_page, os.getenv("TEAM_ID"))
        await browser.close()

        return game_data
