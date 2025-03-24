import os
import pickle
import sys
import base64
import re
from urllib.parse import quote
import requests
import json

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup

# for running locally
import config
PSA_USERNAME = config.psa_username
PSA_PASSWORD = config.psa_password
#
FTP_HOST = config.ftp_host
FTP_USERNAME = config.ftp_username
FTP_PASSWORD = config.ftp_password

CHROMEDRIVER_PATH = config.chromedriver_path

# PSA_USERNAME = os.environ['PSA_USERNAME']
# PSA_PASSWORD = os.environ['PSA_PASSWORD']
# #
# FTP_HOST = os.environ['FTP_HOST']
# FTP_USERNAME = os.environ['FTP_USERNAME']
# FTP_PASSWORD = os.environ['FTP_PASSWORD']

###########################
# log into google account #
###########################

sys.stdout.write('Checking google credentials...')

# set scope to access Gmail API
SCOPES = ['https://mail.google.com/']

credentials = None

home_folder = os.path.expanduser('~')
pickle_path = 'token.pickle'
cred_path = 'credentials.json'

# home_folder = os.path.expanduser('~')
# pickle_path = os.path.join(home_folder, 'token.pickle')
# cred_path = os.path.join(home_folder, 'credentials.json')

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

subject = 'grade-fetcher request'

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

########################
# log into PSA account #
########################

# set options for browser
chrome_options = Options()
#chrome_options.add_argument('--headless')  # Run Chrome in headless mode
#chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--incognito')
chrome_service = Service(CHROMEDRIVER_PATH) # Specify the path to chromedriver executable

# the browser
driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

sys.stdout.write(f'Attempting to sign into PSA account...')

try:
    
    # navigate to PSA login
    driver.get('https://app.collectors.com/signin?b=PSA&r=http://www.psacard.com/myaccount?site%3Dpsa')
        
    wait = WebDriverWait(driver, 100)
    email_element = wait.until(EC.presence_of_element_located((By.ID, 'email')))
    
    # Find the input element with id="email" and enter an email
    email_input = driver.find_element(By.ID, 'email')
    email_input.send_keys(PSA_USERNAME)
    
    # Find the button with type="submit" and click it
    submit_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
    submit_button.click()
    
    # Wait until the page is loaded
    wait = WebDriverWait(driver, 100)  # Adjust the timeout as needed
    password_element = wait.until(EC.presence_of_element_located((By.ID, 'password')))
    
    # Find the element with id="password" and enter the password
    password_input = driver.find_element(By.ID, 'password')
    password_input.send_keys(PSA_PASSWORD)
    
    # Find the button with type="submit" and click it
    login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
    login_button.click()
    
    # Wait until the page is loaded
    wait = WebDriverWait(driver, 100)  # Adjust the timeout as needed
    title = wait.until(EC.title_is('Home'))
    
    sys.stdout.write('success!\n')
    
except Exception as e:

    driver.quit()
    sys.stdout.write(f'failed: {e}\n')
    exit(1)
                
##################
# For each email #
##################
for index, message in enumerate(messages):
    
    sys.stdout.write(f'Working on email {index+1}...')
    
    ##########################################
    # Extract the link and go to the webpage #
    ##########################################
    msg = gmail_service.users().messages().get(userId='me', id=message['id'], format='full').execute()
    payload = msg['payload']
    
    # Find the part of the payload that contains the body
    body = None
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                body = part['body']
                break
    
    submission_number = 0
    order_number = 0
    
    # Extract the body content
    if body:
        body_data = body.get('data')
        if body_data:
            payload_text_decoded = base64.urlsafe_b64decode(body_data).decode('utf-8')
    
            # Use regex to extract submission number and order number
            match = re.search(r'(\d+),\s*(\d+)', payload_text_decoded)
            if match:
                submission_number = int(match.group(1))
                order_number = int(match.group(2))
            else:
                print("Submission number and order number not found in the email body.")
                continue
        else:
            print("No body data found in the email.")
            continue
    else:
        print("No text/plain part found in the email payload.")
        continue
    
    #print(submission_number)
    #print(order_number)
    
    # format the request based on the order number
    r1 = f'{{"orderNumber": "{order_number}"}}'
    r2 = f'{{"orderNumber": "{order_number}","depositId":10}}'
    r3 = f'{{"orderNumbers": ["{order_number}"]}}'
    
    # Encode the string into bytes
    r1_bytes = r1.encode()
    r2_bytes = r2.encode()
    r3_bytes = r3.encode()
   
    # encode the string in hex
    r1_hex = r1_bytes.hex()
    r2_hex = r2_bytes.hex()
    r3_hex = r3_bytes.hex()

    # form the json request
    json_r = f'{{"0":"{r1_hex}","1":"{r2_hex}","2":"{r3_hex}"}}'

    json_url = quote(json_r)

    link = f'https://www.psacard.com/api/grading/trpc/orders.getDefaultShippingAddress,orders.getOrderPaymentApiStatus,orders.shippingIntents?batch=1&input={json_url}'
   
    #print(link)
    driver.get(link)
    
    # Wait until the page is loaded
    wait = WebDriverWait(driver, 100)  # Adjust the timeout as needed
    #title = wait.until(EC.title_contains("psacard.com"))
           
    # Get the page source
    page_source = driver.page_source
    
    # Parse HTML
    soup = BeautifulSoup(page_source, 'html.parser')

    # Find the <pre> tag containing JSON data
    pre_tag = soup.find('pre')
   
    # Extract JSON data
    json_data = pre_tag.string.strip()

    # Extract certIdentifiers using regex
    cert_identifiers = re.findall(r'"certIdentifier":"(\d+)"', json_data)

    # Print certIdentifiers
    
    # Initialize HTML table
    html_table = "";
    
    for identifier in cert_identifiers:
        html_table += identifier + "\n";
    
    # Print HTML table
    #print(html_table)
    
    # create the file
    doc_title = str(submission_number) + '.txt'
    sub_folder = 'Submissions/'
    
    if not os.path.exists(sub_folder):
        os.makedirs(sub_folder)

    doc_path = os.path.join(sub_folder, doc_title)
    
    with open(doc_path, 'w') as file:
        # write the content
        file.write(html_table)
        
    # delete the email
    gmail_service.users().messages().delete(userId='me', id=message['id']).execute()
    sys.stdout.write('done!\n')
        
sys.stdout.write('Deleting remaining emails...')

results = gmail_service.users().messages().list(userId='me').execute()
messages = results.get('messages', [])

# Delete each email
for message in messages:
    gmail_service.users().messages().trash(userId='me', id=message['id']).execute()
    
sys.stdout.write('done!\n')

driver.quit()
