from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Set up Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run Chrome in headless mode
chrome_service = Service('/usr/lib/chromium-browser/chromedriver') # Specify the path to chromedriver executable

# Set up Selenium webdriver
driver = webdriver.Chrome(service=chrome_service, options=chrome_options)  # No need for explicit path if Chrome WebDriver is in PATH
url = "https://example.com"  # Replace with your desired URL

# Navigate to the website
driver.get(url)

# Get the page source (HTML)
html = driver.page_source

# Close the webdriver
driver.quit()

# Print the HTML
print(html)
