# grade-fetcher
Automatically fetch grades from PSA account. This project works in tandem with the 
[Sub Tracker](https://github.com/Level-Up-Subs/sub-tracker) project. Version 2 works with 
[Sub Tracker](https://github.com/Level-Up-Subs/sub-tracker), 
[Grade Server](https://github.com/Level-Up-Subs/grade-server),
and [PSA Grades](https://github.com/Level-Up-Subs/psa-grade).

## Version 1
* user enters submission number
* call to PSA API with sub number
* returns status (and order number)
* if the order is done, checks grade-fetch repo for submission
* if the submission exists in the repo, display the data
* else, send an email to psagradetracker@gmail.com with order number
* cron job on local computer that runs every hour
    * log into psa
    * navigate to order page
    * get grade data and save it to a file in the repo
    * push changes to github
    
### Requirements
* config.py
* credentials.json
* token.pickle
    
## Version 2
* user enters submission number
* call to PSA API with sub number
* returns status (and order number)
* if the order is done, checks psa-grades repo for submission
* if the submission exists in the repo, display the data
* else, make a request to the server with the sub and order number



## Functionality
What does this program do? PSA doesn't have a good API so users can't fetch their grades with a given submission number. Here is an overview of what the program does.
1. Log into a google account
2. Scan all emails for the subject line: "Your PSA grades are available"
3. Log into a PSA account (must be account linked with the emails). The program will attempt to login 5 times.
4. Connect to an FTP server. (This will be changed in the future. The plan is to upload the files to a github repo instead of a server).
5. for each email
  * Extract the PSA link and navigate to the URL
  * Get the HTML, extract the table embedded in the page and adjust the table
  * create a txt file with the extracted table
  * upload the file to the FTP folder. the name of the file is the submission number.
  * delete the email

## Current Setup
* install packages via `pip3 install -r requirements.txt`
* install chromedriver `brew install chromedriver`
* find the path for chromedriver using `type chromedriver` and update the path in the script
* grant cron full disk access (for MacOS): `chmod +x automatic.py`
* create a cron job to run the script whenever you want. use `which python3` for the path. ` 0 */3 * * * cd ~/Developer/projects/LevelUpSubs/grade-fetcher && /usr/local/bin/python3 automatic.py >> Logs/output_$(date +\%Y\%m\%d_\%H\%M\%S).txt 2>&1`
### Required Files
#### config.py
```Python
psa_username = "yourPSAemail@here.com"
psa_password = "yourPSApasswordhere"

ftp_host = "your-server.com"
ftp_username = "yourUsername"
ftp_password = "yourPassword"
```
#### credentials.json
Get this file by following instructions here: https://developers.google.com/gmail/api/quickstart/python

## Future Setup
Check out the `python-app.yml` int the `.github/workflows` repo. You'll also need to add the credentials from `config.py` as secrets for the repo.

### Required Files
#### token.pickle.gpg
This is an encrypted token file. Github actions can't "login" to a google account so run the `manual.py` script and it will create a token file. Encrypt the file with `gpg --symmetric --cipher-algo AES256 token.pickle`. Add the `token.pickle.gpg` file to the repo.

Note: see [here](https://docs.github.com/en/actions/security-guides/encrypted-secrets) for more info

# Cron
`0 */3 * * * cd ~/Developer/projects/LevelUpSubs/grade-fetcher && ./run.sh >/dev/null 2>&1`

# Newest additions
use `base64 -i <file> -o <file>.base64` on token.pickle and credentials.json and add to github actions secrets
