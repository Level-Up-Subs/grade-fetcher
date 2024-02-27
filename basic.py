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

home_folder = os.path.expanduser('~')
pickle_path = os.path.join(home_folder, 'token.pickle')
cred_path = os.path.join(home_folder, 'credentials.json')

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