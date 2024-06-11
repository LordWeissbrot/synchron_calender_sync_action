import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import logging
import logging.handlers
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# Load environment variables from credentials.env file
# load_dotenv('credentials.env')

# Retrieve credentials from environment variables
username = os.getenv('USERNAME')
password = os.getenv('PASSWORD')
client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')
refresh_token = os.getenv('REFRESH_TOKEN')

base_url = 'https://login.synchron.de'
login_url = 'https://login.synchron.de/login?is_app=0'
appointments_url = 'https://login.synchron.de/events?is_app=0'

# Create a session
session = requests.Session()

# Send a GET request to the base URL to retrieve the CSRF token
response = session.get(base_url)
soup = BeautifulSoup(response.text, 'html.parser')
csrf_token_element = soup.find('input', {'name': '_token'})
csrf_token = csrf_token_element['value'] if csrf_token_element else ''

# Prepare the login payload
login_payload = {
    'username': username,
    'password': password,
    '_token': csrf_token
}

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger_file_handler = logging.handlers.RotatingFileHandler(
    "status.log",
    maxBytes=1024 * 1024,
    backupCount=1,
    encoding="utf8",
)
logger_file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger_file_handler.setFormatter(formatter)
logger.addHandler(logger_file_handler)

# Log the CSRF token retrieval
logger.info(f"Retrieved CSRF token: {csrf_token}")

# Send a POST request to the login URL with the login payload
login_response = session.post(login_url, data=login_payload)
logger.info(f"Login response status: {login_response.status_code}")

appointments = []

# Check if the login was successful
if login_response.status_code == 200 and 'Termine' in login_response.text:
    # Send a GET request to the appointments page
    appointments_response = session.get(appointments_url)
    appointments_html = appointments_response.text

    # Parse the HTML using BeautifulSoup
    soup = BeautifulSoup(appointments_html, 'html.parser')

    # Find all the appointment rows
    appointment_rows = soup.find_all('tr', style='color: black; background: whitesmoke')[:5]  # Only take the first 5 entries

    for row in appointment_rows:
        columns = row.find_all('td')
        if len(columns) == 5:
            date_element = row.find_previous('tr', style='color: white; background: #9BC7E6; width: 100px')
            date = date_element.find_all('td')[1].get_text(strip=True) if date_element else ''

            time_range = columns[0].get_text(strip=True).replace('\n', ' ')
            start_time = time_range[:5]  # First 5 characters for start time
            end_time = time_range[5:].strip()  # Remaining characters for end time

            studio_name_element = columns[1].find('b')
            studio_name = studio_name_element.get_text(strip=True) if studio_name_element else ''

            address = columns[1].get_text(strip=True).replace(studio_name, '').strip()

            appointment = {
                'date': date,
                'start_time': start_time,
                'end_time': end_time,
                'studio_name': studio_name,
                'address': address
            }
            appointments.append(appointment)

    # Log the extracted appointments
    for appointment in appointments:
        logger.debug(f"Appointment: {appointment['date']}, {appointment['start_time']} - {appointment['end_time']}, {appointment['studio_name']}, {appointment['address']}")
else:
    logger.error('Login failed. Please check your credentials.')

def authenticate_google_api():
    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )
    service = build('calendar', 'v3', credentials=creds)
    return service

def fetch_future_events(service):
    now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    events_result = service.events().list(
        calendarId='primary',
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    return events

def event_exists(service, summary, start_time, end_time):
    time_min = (start_time - timedelta(minutes=1)).isoformat() + 'Z'
    time_max = (end_time + timedelta(minutes=1)).isoformat() + 'Z'
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    for event in events:
        if event['summary'] == summary and event['start']['dateTime'] == start_time.isoformat() + 'Z' and event['end']['dateTime'] == end_time.isoformat() + 'Z':
            return True
    return False

def main():
    # Filter out past appointments
    current_date = datetime.now()
    future_appointments = []

    for appointment in appointments:
        start_datetime_str = f"{appointment['date']} {appointment['start_time']}"
        start_datetime = datetime.strptime(start_datetime_str, '%d.%m.%Y %H:%M')

        if start_datetime >= current_date:
            future_appointments.append(appointment)

    # Log the future appointments for testing
    logger.debug("Future appointments from Synchron.de:")
    for appointment in future_appointments:
        logger.debug(f"Date: {appointment['date']}, Start Time: {appointment['start_time']}, End Time: {appointment['end_time']}, Studio: {appointment['studio_name']}, Address: {appointment['address']}")

    # Authenticate Google Calendar API
    service = authenticate_google_api()

    # Fetch future events from Google Calendar
    future_events = fetch_future_events(service)
    logger.debug("Future events from Google Calendar:")
    for event in future_events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        logger.debug(f"Summary: {event['summary']}, Start: {start}, End: {end}")

    # Log the appointments that would get created
    logger.debug("Appointments to be created in Google Calendar:")
    for appointment in future_appointments:
        start_datetime_str = f"{appointment['date']} {appointment['start_time']}"
        end_datetime_str = f"{appointment['date']} {appointment['end_time']}"
        start_datetime = datetime.strptime(start_datetime_str, '%d.%m.%Y %H:%M')
        end_datetime = datetime.strptime(end_datetime_str, '%d.%m.%Y %H:%M')

        if not event_exists(service, appointment['studio_name'], start_datetime, end_datetime):
            logger.debug(f"Date: {appointment['date']}, Start Time: {appointment['start_time']}, End Time: {appointment['end_time']}, Studio: {appointment['studio_name']}, Address: {appointment['address']}")

# Example logging for another task (weather fetching)
try:
    SOME_SECRET = os.environ["SOME_SECRET"]
except KeyError:
    SOME_SECRET = "Token not available!"
    logger.error("Token not available!")

if __name__ == "__main__":
    main()
    logger.info(f"Token value: {SOME_SECRET}")

    r = requests.get('https://weather.talkpython.fm/api/weather/?city=Berlin&country=DE')
    if r.status_code == 200:
        data = r.json()
        temperature = data["forecast"]["temp"]
        logger.info(f'Weather in Berlin: {temperature}')
    else:
        logger.error(f'Failed to fetch weather data, status code: {r.status_code}')
