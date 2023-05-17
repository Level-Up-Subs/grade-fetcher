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

from bs4 import BeautifulSoup

# Scopes required for accessing Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/documents']

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
            
            table = extract_table_from_html(page_source)
            
            file.write(table)

        # Use regex to find the number after "Submission"
        match = re.search(r"Submission (\d+)", driver.title)

        if match:
            submission_number = match.group(1)
            print(f"The submission number is: {submission_number}")
            
            # print(extract_table_from_html(page_source))
            create_google_doc_and_write_content(submission_number, extract_table_from_html(page_source))
        else:
            print("No submission number found.")


        driver.quit()

        print(f"Webpage downloaded successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

def create_google_doc_and_write_content(doc_title, content):
    """Creates a new Google Doc with the given title and writes content into it."""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Create a new Docs API service.
    service = build('docs', 'v1', credentials=creds)

    # Create a new Google Doc.
    document = service.documents().create(
        body={'title': doc_title}
    ).execute()

    # Retrieve the document ID.
    document_id = document['documentId']

    # Insert the content into the document.
    requests = [
        {
            'insertText': {
                'location': {
                    'index': 1
                },
                'text': content
            }
        }
    ]
    service.documents().batchUpdate(
        documentId=document_id,
        body={'requests': requests}
    ).execute()

    print(f"New Google Doc created. ID: {document_id}")

def extract_table_from_html(html_data):
    """Extracts the first <table> element from the given HTML data."""
    soup = BeautifulSoup(html_data, 'html.parser')
    table = soup.find('table')
    
    table = remove_column_from_table(table, "Cert Image")
    
    return str(table)
    
def remove_column_from_table(table, column_name):
    """Removes the column with the specified data-title attribute from the given table."""
    # Find the column index based on the column name
    column_index = None
    headers = table.find('tr').find_all('th')
    for i, header in enumerate(headers):
        if header.get('data-title') == column_name:
            column_index = i
            break
    
    # Remove the column from each row in the table
    rows = table.find_all('tr')
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if column_index is not None and column_index < len(cells):
            cells[column_index].decompose()
    
    return table

if __name__ == '__main__':
    subject_to_find = 'Your PSA grades are available'
    find_emails_with_subject(subject_to_find)
