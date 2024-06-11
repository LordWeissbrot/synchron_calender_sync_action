import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import logging
import logging.handlers

# Load environment variables from credentials.env file
load_dotenv('credentials.env')

# Retrieve credentials from environment variables
username = os.getenv('USERNAME')
password = os.getenv('PASSWORD')

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
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger_file_handler.setFormatter(formatter)
logger.addHandler(logger_file_handler)

# Log the CSRF token retrieval
logger.info(f"Retrieved CSRF token: {csrf_token}")

# Send a POST request to the login URL with the login payload
login_response = session.post(login_url, data=login_payload)
logger.info(f"Login response status: {login_response.status_code}")

# Check if the login was successful
if login_response.status_code == 200 and 'Termine' in login_response.text:
    appointments = []

    # Send a GET request to the appointments page
    appointments_response = session.get(appointments_url)
    appointments_html = appointments_response.text

    # Parse the HTML using BeautifulSoup
    soup = BeautifulSoup(appointments_html, 'html.parser')

    # Find all the appointment rows
    appointment_rows = soup.find_all('tr', style='color: black; background: whitesmoke')

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

            address = columns[1].get_text(strip=True).split('\n')[-1].strip()

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
        logger.info(f"Appointment: {appointment['date']}, {appointment['start_time']} - {appointment['end_time']}, {appointment['studio_name']}, {appointment['address']}")
else:
    logger.error('Login failed. Please check your credentials.')

# Example logging for another task (weather fetching)
try:
    SOME_SECRET = os.environ["SOME_SECRET"]
except KeyError:
    SOME_SECRET = "Token not available!"
    logger.error("Token not available!")

if __name__ == "__main__":
    logger.info(f"Token value: {SOME_SECRET}")

    r = requests.get('https://weather.talkpython.fm/api/weather/?city=Berlin&country=DE')
    if r.status_code == 200:
        data = r.json()
        temperature = data["forecast"]["temp"]
        logger.info(f'Weather in Berlin: {temperature}')
    else:
        logger.error(f'Failed to fetch weather data, status code: {r.status_code}')
