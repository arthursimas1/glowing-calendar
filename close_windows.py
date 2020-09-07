import pickle
import os.path
import requests
from dateutil import parser as dateParser
from datetime import datetime
from datetime import timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SERVICE_NAME = 'glowing_calendar'
EVENT_NAME = 'close_windows'


# if modifying these scopes, delete the file calendar_token.pickle
SCOPES = ['https://www.googleapis.com/auth/calendar']


def getCredentials():
    creds = None
    # the file calendar_token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time
    if os.path.exists('calendar_token.pickle'):
        with open('calendar_token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # if there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)

        # save the credentials for the next run
        with open('calendar_token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


def getCalendar(creds):
    calendarService = build('calendar', 'v3', credentials=creds)
    return calendarService


def getSunsetTime(date):
    sunstatsAPI = requests.get(f'https://api.sunrise-sunset.org/json?lat=-23.562849&lng=-46.654393&date={date}&formatted=0') # using Paulista Avenue coordinates

    if sunstatsAPI.status_code != 200 or (sunstats := sunstatsAPI.json())['status'] != 'OK':
        raise RuntimeError('[api.sunrise-sunset.org] something went wrong.')

    sunsetISO = sunstats['results']['sunset']
    sunsetDT = dateParser.isoparse(sunsetISO)
    return sunsetDT


def getNext10Events(calendar):
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """

    # Call the Calendar API
    now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    print('getting the upcoming 10 events')
    events = calendar.events().list(calendarId='primary', timeMin=now,
                                    maxResults=10, singleEvents=True,
                                    orderBy='startTime').execute()

    if not events:
        print('no upcoming events found.')

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        #print(start, event['summary'])
        print(event)


def getNextCloseWindowsEvent(calendarEvents):
    now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
    events = calendarEvents.list(calendarId='primary', timeMin=now,
                                 q=f':~:{SERVICE_NAME}:~:|{EVENT_NAME}',
                                 maxResults=5, singleEvents=True,
                                 orderBy='startTime').execute()
    return events.get('items', [])


def setCloseWindowsEvent(calendarEvents):
    # get next sunset time
    next_day = (datetime.utcnow() + timedelta(days=1)).isoformat()[:10] # get only date information
    sunsetDT = getSunsetTime(next_day)

    print(f'next sunset time: {sunsetDT}')

    event = {
        'summary': 'close all windows',
        'location': 'my house',
        'description': f':~:{SERVICE_NAME}:~:|{EVENT_NAME}',
        'start': {
            'dateTime': sunsetDT.isoformat()
        },
        'end': {
            'dateTime': (sunsetDT + timedelta(minutes=10)).isoformat()
        },
        'reminders': {
            'useDefault': False,
            'overrides': [{
                'method': 'popup',
                'minutes': 0,
            }],
        },
    }
    calendarEvents.insert(calendarId='primary', body=event).execute()
    print('scheduled!')


if __name__ == '__main__':
    # setup calendar service
    creds = getCredentials()
    calendar = getCalendar(creds)
    events = calendar.events()

    #print(getNextCloseWindowsEvent(events))
    setCloseWindowsEvent(events)
