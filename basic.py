import os
import pickle
import sys
import base64
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

###########################
# log into google account #
###########################

sys.stdout.write('Checking google credentials...')

# set scope to access Gmail API
SCOPES = ['https://mail.google.com/']

credentials = None

pickle_path = 'token.pickle'
cred_path = 'credentials.json'

# check if credentials already exist
if os.path.exists(pickle_path):
    with open(pickle_path, 'rb') as token:
        credentials = pickle.load(token)
else:
    # load credentials from JSON file downloaded from Google Developers Console
    if not os.path.exists(cred_path):
        sys.stdout.write('missing credentials.json file')
        exit(1)
        
    flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
    credentials = flow.run_local_server(port=0)
    
    # Save credentials for future use
    with open(pickle_path, 'wb') as token:
        pickle.dump(credentials, token)

sys.stdout.write('complete!\n')

#######################################
# find all emails with matching title #
#######################################

# Build the Gmail API service
gmail_service = build('gmail', 'v1', credentials=credentials)

subject = 'Your PSA grades are available'

results = gmail_service.users().messages().list(userId='me', labelIds=['INBOX'], q=f'subject:"{subject}"').execute()
messages = results.get('messages', [])

if not messages:
    sys.stdout.write(f'No emails with subject: {subject}.\n')
    
    sys.stdout.write('Deleting all emails...')
    
    results = gmail_service.users().messages().list(userId='me').execute()
    messages = results.get('messages', [])

    # Delete each email
    for message in messages:
        gmail_service.users().messages().trash(userId='me', id=message['id']).execute()
        
    sys.stdout.write('done!\n')
    
    exit(0)
    
sys.stdout.write(f'{len(messages)} email(s) found with matching subject: {subject}.\n')