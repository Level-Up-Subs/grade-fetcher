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

from ftplib import FTP

# Scopes required for accessing Gmail API
SCOPES = ['https://mail.google.com/']

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
                    if download_webpage(link):
                                    service.users().messages().delete(userId='me', id=message['id']).execute()

def delete_emails():
    # Subject of the emails to delete
    SUBJECT = 'Your PSA grades are available'
    
    # Get credentials
    credentials = get_credentials()
    service = build('gmail', 'v1', credentials=credentials)
    
    # Search for emails with the specified subject
    response = service.users().messages().list(userId='me', q=f'subject:"{SUBJECT}"').execute()
    messages = response.get('messages', [])
    
    if messages:
        # Delete the matching emails
        for message in messages:
            service.users().messages().delete(userId='me', id=message['id']).execute()
    
        print(f'{len(messages)} email(s) with the subject "{SUBJECT}" deleted.')
    else:
        print(f'No emails with the subject "{SUBJECT}" found.')

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
        email_input.send_keys(config.psa_username)

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
        password_input.send_keys(config.psa_password)

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
        # filename = 'webpage.html'
        # with open(filename, 'w', encoding='utf-8') as file:
        #
        #     table = extract_table_from_html(page_source)
        #
        #     file.write(table)

        # Use regex to find the number after "Submission"
        match = re.search(r"Submission (\d+)", driver.title)

        if match:
            submission_number = match.group(1)
            print(f"The submission number is: {submission_number}")
            
            extracted_table = extract_table_from_html(page_source)
            adjusted_table = adjust_table(extracted_table)
            
            upload_file_to_namecheap(submission_number + ".txt", adjusted_table)
        else:
            print("No submission number found.")


        driver.quit()

        print(f"Webpage downloaded successfully.")
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def upload_file_to_namecheap(doc_title, content):
    # Connect to the FTP server
    ftp = FTP(config.ftp_host)
    ftp.login(config.ftp_username, config.ftp_password)
    
    # Change to the desired remote directory
    ftp.cwd("public_html")
    
    # create the file
    with open(doc_title, 'w') as file:
        # write the content
        file.write(content)
        
    # Open the local file in binary mode for uploading
    with open(doc_title, 'rb') as file:
        # Upload the file to the FTP server
        ftp.storbinary(f'STOR {doc_title}', file)
        
    os.remove(doc_title)
        
    ftp.quit()

def extract_table_from_html(html_data):
    """Extracts the first <table> element from the given HTML data."""
    soup = BeautifulSoup(html_data, 'html.parser')
    table = soup.find('table')
    
    # Find the table header row
    header_row = soup.find('thead').find('tr')
    
    # Find the index of the "Images" column
    line_column_index = 0
    images_column_index = 5
    type_column_index = 6

    # Remove the "Images" column from the header row
    header_row.find_all('th')[type_column_index].extract()
    header_row.find_all('th')[images_column_index].extract()
    header_row.find_all('th')[line_column_index].extract()
    
    # Find the table body rows
    body_rows = soup.find('tbody').find_all('tr')
    
    # Remove the "Images" column from each body row
    for row in body_rows:
        row.find_all('td')[type_column_index].extract()
        row.find_all('td')[images_column_index].extract()
        row.find_all('td')[line_column_index].extract()
    
        # Remove the <a> tag from the "Cert #" columns in each body row
        cert_column = row.find('td', {'data-title': 'Cert #'})
        if cert_column is not None and cert_column.a:
            cert_column.a.unwrap()
    
    return str(table)
    
def adjust_table(html):
    # Parse the HTML input
    soup = BeautifulSoup(html, 'html.parser')

    # Find all table elements
    tables = soup.find_all('table')

    # Iterate through each table
    for table in tables:
        # Find all rows in the table
        rows = table.find_all('tr')

        # Iterate through each row
        for row in rows:
            # Find all cells in the row
            cells = row.find_all(['td', 'th'])

            # Check if the row has at least 3 cells
            if len(cells) >= 3:
                # Set the width of the 3rd column to 50%
                cells[3]['style'] = 'width: 50%;'

        # Add black border lines between rows
        table['style'] = 'border-collapse: collapse; border: 1px solid black;'
        
    # Return the modified HTML
    return soup.prettify()

if __name__ == '__main__':
    subject_to_find = 'Your PSA grades are available'
    find_emails_with_subject(subject_to_find)
