import sys

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# config data
import config
CHROMEDRIVER_PATH = config.chromedriver_path

PSA_USERNAME = config.psa_username
PSA_PASSWORD = config.psa_password

from bs4 import BeautifulSoup

import requests
import json
import base64

GH_USER = config.github_user
GH_EMAIL = config.github_email
GH_TOKEN = config.github_token

# get the arg count
argc = len(sys.argv)

# check to see that only one argument was provided
if argc < 3:
    print('must provide sub number and order number')
    exit(1)
elif argc > 3:
    print('too many args')
    exit(1)
 
sub_number = sys.argv[1]
order_number = sys.argv[2]

# argument must be a number
if not sub_number.isdigit():
    print(f'invalid sub number: {sub_number}')
    exit(1)
    
if not order_number.isdigit():
    print(f'invalid order number: {order_number}')
    exit(1)
    
url = f'https://www.psacard.com/myaccount/myorder?o={order_number}'

# log into PSA account
# set options for browser
chrome_options = Options()
#chrome_options.add_argument('--headless')  # Run Chrome in headless mode
chrome_options.add_argument('--disable-gpu')
chrome_service = Service(CHROMEDRIVER_PATH) # Specify the path to chromedriver executable

# the browser
driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
step = 0

try:
    # navigate to PSA login
    driver.get('https://app.collectors.com/signin?b=PSA&r=https:%2f%2fwww.psacard.com%2fmyaccount')
    
    step = 1
    
    wait = WebDriverWait(driver, 100)
    email_element = wait.until(EC.presence_of_element_located((By.ID, 'email')))
        
    # Find the input element with id="email" and enter an email
    email_input = driver.find_element(By.ID, 'email')
    email_input.send_keys(PSA_USERNAME)
    
    # Find the button with type="submit" and click it
    submit_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
    submit_button.click()
    
    step = 2
    
    # Wait until the page is loaded
    wait = WebDriverWait(driver, 10)  # Adjust the timeout as needed
    password_element = wait.until(EC.presence_of_element_located((By.ID, 'password')))
    
    # Find the element with id="password" and enter the password
    password_input = driver.find_element(By.ID, 'password')
    password_input.send_keys(PSA_PASSWORD)
    
    # Find the button with type="submit" and click it
    login_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
    login_button.click()
    
    step = 3
    
    # Wait until the page is loaded
    wait = WebDriverWait(driver, 100)  # Adjust the timeout as needed
    title = wait.until(EC.title_is('My Membership'))
    
except Exception as e:
    driver.quit()
    print('Failed to login to PSA website: step {step}')
    exit(1)

# navigate to the grades page
driver.get(url)

# Wait until the page is loaded
wait = WebDriverWait(driver, 100)  # Adjust the timeout as needed
title = wait.until(EC.title_contains("Order"))

# Get the page source
page_source = driver.page_source

# extract the table
soup = BeautifulSoup(page_source, 'html.parser')
table = soup.find('table')

# TODO: sanitize the data

html_out = str(table)

# push the data to the psa-grade repo

# Repository details
owner = "Level-Up-Subs"
repo_name = "psa-grades"

# API endpoint for updating file content
url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/submissions/{sub_number}.txt"

# Base64 encode HTML content
encoded_content = base64.b64encode(html_out.encode()).decode()

# Request headers
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GH_TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28"
}

# Request body
payload = {
    "message": "adding submission",
    "committer": {
        "name": GH_USER,
        "email": GH_EMAIL
    },
    "content": encoded_content
}

# Make PUT request
response = requests.put(url, headers=headers, json=payload)

# Check response
if response.status_code == 200:
    print("File content updated successfully.")
else:
    print("Failed to update file content. Status code:", response.status_code)
    print("Response:", response.text)
    exit(1)

