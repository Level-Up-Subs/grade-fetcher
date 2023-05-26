import os
import pickle
import sys
import base64
import re

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

import config

from bs4 import BeautifulSoup

from ftplib import FTP

###########################
# log into google account #
###########################

sys.stdout.write('Checking google credentials...')

# set scope to access Gmail API
SCOPES = ['https://mail.google.com/']

credentials = None

# check if credentials already exist
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        credentials = pickle.load(token)
else:
    # load credentials from JSON file downloaded from Google Developers Console
    if not os.path.exists('credentials.json'):
        sys.stdout.write('missing credentials.json file')
        exit()
        
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    credentials = flow.run_local_server(port=0)
    
    # Save credentials for future use
    with open('token.pickle', 'wb') as token:
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
    exit()
    
sys.stdout.write(f'{len(messages)} email(s) found with matching subject: {subject}.\n')

########################
# log into PSA account #
########################
attempts = 0
max_attempts = 5

# set options for browser
chrome_options = Options()
chrome_options.add_argument('--headless')  # Run Chrome in headless mode
chrome_options.add_argument('--disable-gpu')
chrome_service = Service('/opt/homebrew/bin/chromedriver')  # Specify the path to chromedriver executable

# the browser
driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

while attempts < max_attempts:

    sys.stdout.write(f'Attempt #{attempts+1} to sign into PSA account...')

    try:
    
        # navigate to PSA login
        driver.get('https://app.collectors.com/signin?b=PSA&r=http://www.psacard.com/myaccount?site%3Dpsa')
        
        # Find the input element with id="email" and enter an email
        email_input = driver.find_element(By.ID, 'email')
        email_input.send_keys(config.psa_username)
        
        # Find the button with type="submit" and click it
        submit_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_button.click()
        
        # Wait until the page is loaded
        wait = WebDriverWait(driver, 10)  # Adjust the timeout as needed
        password_element = wait.until(EC.presence_of_element_located((By.ID, 'password')))
        
        # Find the element with id="password" and enter the password
        password_input = driver.find_element(By.ID, 'password')
        password_input.send_keys(config.psa_password)
        
        # Find the button with type="submit" and click it
        login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        login_button.click()
        
        # Wait until the page is loaded
        wait = WebDriverWait(driver, 100)  # Adjust the timeout as needed
        title = wait.until(EC.title_is('My Membership'))
        
        sys.stdout.write('success!\n')
        break
        
    except Exception as e:
    
        driver.quit()
        
        sys.stdout.write(f'failed: {e}\n')
        attempts += 1
        
        if attempts is max_attempts:
            sys.stdout.write('Ran out of attempts...script will run again in 6 hours.\n')
            exit()
        
#######################
# log into FTP server #
#######################
# Connect to the FTP server
ftp = FTP(config.ftp_host)
ftp.login(config.ftp_username, config.ftp_password)

# Change to the desired remote directory
ftp.cwd("public_html")
        
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
    
    # get the email body
    body = None
    
    if 'parts' in payload:
        for part in payload['parts']:
            if 'body' in part:
                body_data = part['body']
                if 'data' in body_data:
                    body = base64.urlsafe_b64decode(body_data['data']).decode()
    elif 'body' in payload:
        body_data = payload['body']
        if 'data' in body_data:
            body = base64.urlsafe_b64decode(body_data['data']).decode()

    # extract the link
    link = None
    
    if body:
        link_pattern = r'(https://www\.psacard\.com/myaccount/myorder\S*)'
        match = re.search(link_pattern, body)
        if match:
            link =  match.group(0)
            link = link[:-1]
   
    # navigate to the URL
    if link:
        driver.get(link)
        
        # Wait until the page is loaded
        wait = WebDriverWait(driver, 100)  # Adjust the timeout as needed
        title = wait.until(EC.title_contains("Order"))
        
        # Get the page source
        page_source = driver.page_source

        # extract the table
        soup = BeautifulSoup(page_source, 'html.parser')
        table = soup.find('table')
        
         # Find the table header row
        header_row = soup.find('thead').find('tr')
        
        # indices for columns that will be removed
        line_column_index = 0
        images_column_index = 5
        type_column_index = 6

        # Remove the columns from the header row
        header_row.find_all('th')[type_column_index].extract()
        header_row.find_all('th')[images_column_index].extract()
        header_row.find_all('th')[line_column_index].extract()
        
        # Find the table body rows
        body_rows = soup.find('tbody').find_all('tr')
        
        # Remove the columns from each body row
        for row in body_rows:
            row.find_all('td')[type_column_index].extract()
            row.find_all('td')[images_column_index].extract()
            row.find_all('td')[line_column_index].extract()
        
            # Remove the <a> tag from the "Cert #" columns in each body row
            cert_column = row.find('td', {'data-title': 'Cert #'})
            if cert_column is not None and cert_column.a:
                cert_column.a.unwrap()
                
        # adjust the table
        tables = soup.find_all('table')

        # Iterate through each table
        for t in tables:
            # Find all rows in the table
            rows = t.find_all('tr')

            # Iterate through each row
            for row in rows:
                # Find all cells in the row
                cells = row.find_all(['td', 'th'])

                # Check if the row has at least 3 cells
                if len(cells) >= 3:
                    # Set the width of the 3rd column to 50%
                    cells[3]['style'] = 'width: 50%;'

            # Add black border lines between rows
            t['style'] = 'border-collapse: collapse; border: 1px solid black;'
        
        # Use regex to find the number after "Submission"
        submission_number = None
        
        match = re.search(r"Submission (\d+)", driver.title)
        if match:
            submission_number = match.group(1)
        
        html_out = str(table)
        
        # Save the page source as a file
        # filename = 'webpage.html'
        # with open(filename, 'w', encoding='utf-8') as file:
        #     file.write(html_out)
            
        # create the file
        doc_title = submission_number + '.txt'
        
        with open(doc_title, 'w') as file:
            # write the content
            file.write(html_out)
            
        # Open the local file in binary mode for uploading
        with open(doc_title, 'rb') as file:
            # Upload the file to the FTP server
            ftp.storbinary(f'STOR {doc_title}', file)
        
        os.remove(doc_title)
            
        # delete the email
        gmail_service.users().messages().delete(userId='me', id=message['id']).execute()
        sys.stdout.write('done!\n')

driver.quit()
ftp.quit()
