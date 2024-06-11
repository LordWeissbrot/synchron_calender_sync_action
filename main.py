import os
import logging
import logging.handlers
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger_file_handler = logging.handlers.RotatingFileHandler(
    "status.log",
    maxBytes=1024 * 1024,
    backupCount=1,
    encoding="utf8",
)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger_file_handler.setFormatter(formatter)
logger.addHandler(logger_file_handler)

# Retrieve credentials from environment variables
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
refresh_token = os.getenv('REFRESH_TOKEN')

def create_google_calendar_event():
    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )
    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': 'TestEventCrawler',
        'location': 'Test Location',
        'start': {
            'dateTime': '2024-06-12T09:00:00',
            'timeZone': 'Europe/Berlin',
        },
        'end': {
            'dateTime': '2024-06-12T11:00:00',
            'timeZone': 'Europe/Berlin',
        },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()
    logger.info(f"Event created: {event.get('htmlLink')}")

if __name__ == "__main__":
    create_google_calendar_event()
    logger.info("Test event created successfully.")
