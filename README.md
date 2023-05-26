# grade-fetcher
Automatically fetch grades from PSA account

## Setup

`pip3 install -r requirements.txt`
`brew install chromedriver`
* make sure to grant cron full disk access if on MacOS
`chmod +x script.py`
`which python3` for crontab path

### Required files
#### config.py
```Python
username = "yourPSAemail@here.com"
password = "yourPSApasswordhere"
```
#### credentials.json
Get this file by following instructions here: https://developers.google.com/gmail/api/quickstart/python

## Description
What does this script actually do?
* searches through a gmail account for emails with the subject line: "Your PSA grades are available"
* grabs the link in the email that starts with "https://www.psacard.com/myaccount/myorder"
* opens a browser via selenium and navigates to PSA
* logins in using the credentials in `config.py`
* saves the order page as an html file
