import os
import pickle
import re
import time
import base64
import webbrowser
import urllib
import config

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Scopes required for accessing Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_credentials():
    # Check if credentials already exist
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)
    else:
        # Load credentials from JSON file downloaded from Google Developers Console
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        credentials = flow.run_local_server(port=0)
        # Save credentials for future use
        with open('token.pickle', 'wb') as token:
            pickle.dump(credentials, token)
    return credentials

def find_emails_with_subject(subject):
    # Get credentials
    credentials = get_credentials()

    # Build the Gmail API service
    service = build('gmail', 'v1', credentials=credentials)

    # Call the Gmail API to search for emails with the specified subject
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], q=f'subject:"{subject}"').execute()
    messages = results.get('messages', [])

    if not messages:
        print(f'No emails found with the subject: "{subject}"')
    else:
        print(f'Emails with the subject "{subject}":')
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
            payload = msg['payload']
            headers = payload['headers']
            for header in headers:
                if header['name'] == 'Subject':
                    email_subject = header['value']
                    print('Subject:', email_subject)
            body = get_email_body(payload)
            if body:
                link = extract_link_from_body(body)
                if link:
                    link = link[:-1]
                    print('Link:', link)
                    download_webpage(link)

def get_email_body(payload):
    if 'parts' in payload:
        for part in payload['parts']:
            if 'body' in part:
                body_data = part['body']
                if 'data' in body_data:
                    body = base64.urlsafe_b64decode(body_data['data']).decode()
                    return body
    elif 'body' in payload:
        body_data = payload['body']
        if 'data' in body_data:
            body = base64.urlsafe_b64decode(body_data['data']).decode()
            return body
    return None

def extract_link_from_body(body):
    link_pattern = r'(https://www\.psacard\.com/myaccount/myorder\S*)'
    match = re.search(link_pattern, body)
    if match:
        return match.group(0)
    return None

def download_webpage(url):
    try:
        options = Options()
        options.add_argument('--headless')  # Run Chrome in headless mode
        options.add_argument('--disable-gpu')
        service = Service('/opt/homebrew/bin/chromedriver')  # Specify the path to chromedriver executable
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)

        print("Entering email")

        # Find the input element with id="email" and enter an email
        email_input = driver.find_element(By.ID, 'email')
        email_input.send_keys(config.username)

        # Find the button with type="submit" and click it
        submit_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_button.click()
        
        print("Email submitted")
        
        # Wait until the page is loaded
        wait = WebDriverWait(driver, 10)  # Adjust the timeout as needed
        password_element = wait.until(EC.presence_of_element_located((By.ID, 'password')))

        print("Entering password")
        
        # Find the element with id="password" and enter the password
        password_input = driver.find_element(By.ID, 'password')
        password_input.send_keys(config.password)

        # Find the button with type="submit" and click it
        login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        login_button.click()
        
        print("Password submitted")
        
        # Wait until the page is loaded
        wait = WebDriverWait(driver, 100)  # Adjust the timeout as needed
        title = wait.until(EC.title_is("PSA Collectibles Authentication and Grading Service"))
        
        print("Done logging in")
        
        driver.get(url)
        
        print("Loading order page")
        
        # Wait until the page is loaded
        wait = WebDriverWait(driver, 100)  # Adjust the timeout as needed
        title = wait.until(EC.title_contains("Order"))
        
        print("Order page loaded")
        
        # Get the page source
        page_source = driver.page_source

        # Save the page source as a file
        filename = 'webpage.html'
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(page_source)

        driver.quit()

        print(f"Webpage downloaded successfully. Saved as '{filename}'.")
    except Exception as e:
        print(f"An error occurred while downloading the webpage: {e}")

if __name__ == '__main__':
    subject_to_find = 'Your PSA grades are available'
    find_emails_with_subject(subject_to_find)
