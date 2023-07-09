import os
from dataclasses import dataclass, field
from datetime import datetime
from unicodedata import normalize

from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# NOTE when the token expires, just go to the credentials tab in google cloud projects, delete the old OAuth 2.0 client ID, create a new credential, and change the port to 8000 then back to 0

POKEMON_CALENDAR_ID = os.environ.get("POKEMON_CALENDAR_ID")

# If modifying these scopes, delete the file token.json.
# For a full list of scopes, see 
# https://developers.google.com/identity/protocols/oauth2/scopes#calendar
SCOPES = ["https://www.googleapis.com/auth/calendar"]

GREEN_CHECK_MARK = "\U00002705"
RED_CROSS_MARK = "\U0000274C"

CURRENT_YEAR = datetime.now().year


def parse_date(date: str) -> str:
    """Converts string in the format `Monday, January 13, at 09:00 PM` to the
    following format `2023-01-13 21:00:00`, then returns it"""
    date_format = "%A, %B %d, at %I:%M %p"

    datetime_obj = datetime.strptime(date, date_format)

    day = datetime_obj.strftime("%d")
    month = datetime_obj.strftime("%m")
    time = datetime_obj.strftime("%H:%M")

    parsed_date = f"{CURRENT_YEAR}-{month}-{day} {time}:00"

    return parsed_date


def event_ends_next_year(start_date: str, end_date: str):
    """Returns true if an event with `start_date` and `end_date` ends next year
    (starts in December and ends after December)"""
    start_month = start_date[5:7]
    end_month = end_date[5:7]
    return int(start_month) == 12 and int(end_month) < 12


def is_all_day_event(start_date: str, end_date: str):
    """Returns true if an event with `start_date` and `end_date` is an all day
    event (starts at 00:00:00 and ends at 23:59:00 on the same day)"""
    start_month_and_day = start_date[5:10]
    end_month_and_day = end_date[5:10]
    start_time = start_date[11:]
    end_time = end_date[11:]

    return (
        start_month_and_day == end_month_and_day
        and start_time == "00:00:00"
        and end_time == "23:59:00"
    )


def convert_to_rfc3339(date: str):
    """Converts a string to the rfc3339 format, then returns it"""
    rfc3339_format = "%Y-%m-%dT%H:%M:%S"
    date_object = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")

    return date_object.strftime(rfc3339_format)


def convert_to_yyy_mm_dd(date: str):
    """Returns a string converted to the YYY-MM-DD format"""
    yyy_mm_dd_format = "%Y-%m-%d"
    date_object = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    return date_object.strftime(yyy_mm_dd_format)


@dataclass
class Event:
    start_time: str = field(compare=False)
    end_time: str = field(compare=False)
    summary: str
    description: str

    def to_dict(self):
        if is_all_day_event(self.start_time, self.end_time):
            self.start_time = convert_to_yyy_mm_dd(self.start_time)
            self.end_time = convert_to_yyy_mm_dd(self.end_time)

            metadata = {
                "summary": self.summary,
                "description": self.description,
                "start": {
                    "date": self.start_time
                },
                "end": {
                    "date": self.end_time
                },
            }

        elif event_ends_next_year(self.start_time, self.end_time):
            self.start_time = convert_to_rfc3339(self.start_time)

            # add one to end_time's year
            end_time_date_object = datetime.strptime(self.end_time, "%Y-%m-%d %H:%M:%S")
            end_time_date_object = end_time_date_object + relativedelta(year=1)

            self.end_time = end_time_date_object.strftime("%Y-%m-%d %H:%M:%S")
            self.end_time = convert_to_rfc3339(self.end_time)

            metadata = {
                "summary": self.summary,
                "description": self.description,
                "start": {
                    "dateTime": self.start_time,
                    "timeZone": "UTC-5"
                },
                "end": {
                    "dateTime": self.end_time,
                    "timeZone": "UTC-5"
                },
            }

        else:
            self.start_time = convert_to_rfc3339(self.start_time)
            self.end_time = convert_to_rfc3339(self.end_time)

            metadata = {
                "summary": self.summary,
                "description": self.description,
                "start": {
                    "dateTime": self.start_time,
                    "timeZone": "UTC-5"
                },
                "end": {
                    "dateTime": self.end_time,
                    "timeZone": "UTC-5"
                },
            }

        return metadata

    def get_summary(self):
        return self.summary

    def __str__(self):
        return str(self.to_dict())


def main():
    # NOTE do not delete this, this is all the shit you need for the google calendar API
    creds = None
    # The file token.json stores the user"s access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES)
            creds = flow.run_local_server(port=8000)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    events = []
    driver = webdriver.Firefox()
    url = "https://leekduck.com/events"

    # Go to `url`
    driver.get(url)

    # Save the `url`'s html to be parsed later'
    soup = BeautifulSoup(driver.page_source, "html5lib")

    # Html of everything within <div class="events-list" "current-events">
    soup = soup.find_all("div", class_="current-events")[0]

    # List of all the spans under <div class="events-list" "current-events">
    soup = soup.find_all(
        "span",
        class_="event-header-item-wrapper"
    )

    event_links = set()

    # Span refers to each html block containing the <a> tag we're looking for
    # Let's get rid of all the unannounced events
    for span in soup:
        event_name = span.find("a").get("href")
        if "unannounced" in event_name:
            continue
        link = f"https://leekduck.com{event_name}"
        event_links.add(link)

    # Go to every link, get the end and start dates of the event
    for link in event_links:

        print(f"Parsing {link}... ", end="", flush=True)

        driver.get(link)
        soup = BeautifulSoup(driver.page_source, "html5lib")

        title = soup.find("h1").text.strip()  # type: ignore
        title = normalize("NFKD", title)  # needed because i keep getting "\xa0" on the summary

        # Get the event date and start time. Wait 10 secs after going to the website to allow it to load the necessary elements
        start_date = (
            WebDriverWait(driver, 10)
            .until(EC.presence_of_element_located((By.ID, "event-date-start")))
            .text.strip()
            .rstrip(",")
            .replace("  ", " ")
        )
        start_time = (
            WebDriverWait(driver, 10)
            .until(EC.presence_of_element_located((By.ID, "event-time-start")))
            .text
            .split("M")[0] + "M".replace("  ", " ")
        )

        complete_start_date = f"{start_date}, {start_time}"

        end_date = (
            WebDriverWait(driver, 10)
            .until(EC.presence_of_element_located((By.ID, "event-date-end")))
            .text.strip()
            .rstrip(",")
            .replace("  ", " ")
        )
        end_time = (
            WebDriverWait(driver, 10)
            .until(EC.presence_of_element_located((By.ID, "event-time-end")))
            .text
            .split("M")[0] + "M".replace("  ", " ")
        )

        complete_end_date = f"{end_date}, {end_time}"

        if start_date != "None":
            parsed_start_date = parse_date(complete_start_date)
            parsed_end_date = parse_date(complete_end_date)

            print(f"\r{GREEN_CHECK_MARK}  Done parsing {link}", end="\n", flush=True)

            new_event = Event(parsed_start_date, parsed_end_date, title, link)
            events.append(new_event)

    # NOTE THIS IS WHERE WE ADD EVENTS TO THE CALENDAR
    try:
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API
        events_result = service.events().list(calendarId=POKEMON_CALENDAR_ID, singleEvents=True, orderBy="startTime").execute()

        # We're just gonna use the title of the event to compare it to the list of events we want to add
        calendar_events = [event["summary"] for event in events_result.get("items", [])]  

        if not calendar_events:
            print("No upcoming events found.")
            return

        # If event we parsed is already in our calendar, skip it and go to the next one, otherwise add it to the calendar
        for event in events:
            if event.get_summary() in calendar_events:
                continue
            metadata = event.to_dict()
            added_event = service.events().insert(calendarId=POKEMON_CALENDAR_ID, body=metadata).execute()
            added_event_link = added_event.get("htmlLink")
            print(f"\r{GREEN_CHECK_MARK}  {event.get_summary()} added to calendar {added_event_link}", end="\n", flush=True)


    except HttpError as error:
        print("An error occurred: %s" % error)

    driver.quit()


if __name__ == "__main__":
    main()
