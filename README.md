[Link to the calendar](https://calendar.google.com/calendar/embed?src=0b889e2a88d44497fe2cd00443429815a4f6bbb043dc66cdd3197e15e201963c%40group.calendar.google.com&ctz=America%2FNew_York)

Pogocal is a program written in python that scrapes the website [https://leekduck.com/events/](https://leekduck.com/events/) using a plethora of APIs and adds Pokemon Go events to my Google calendar using the Google Calendar API

# If you want to replicate this for your own time zone, or for your own calendar...

I did not make this pogram to distibute it -- I made it to share the google calendar.

However, if you wish to re-make this program so that events are added to YOUR personal calendar in YOUR timezone, you're gonna need a few things.

## Requirements for replication...

1. Python 3.11.4 or higher
2. [selenium WebDriver](https://pypi.org/project/selenium/)
3. [beautifulsoup4](https://pypi.org/project/beautifulsoup4/)
4. A Google account

## Steps for replication...

1. Clone the repo
2. Change the `MY_TIMEZONE` to whatever your timezone is
3. Change the `POKEMON_CALENDAR_ID` variable to whatever your google calendar ID is
4. Read the [Google Calendar API documentation](https://developers.google.com/calendar/api/quickstart/python)
5. ???
6. PROFIT!!! :D
