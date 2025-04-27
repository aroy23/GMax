from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv
import google.generativeai as genai
import os
import time

# Load credentials
load_dotenv()

email = os.getenv("GMAIL_EMAIL")
password = os.getenv("GMAIL_PASSWORD")
gemini_api_key = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

# Chrome "stealth" options
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument(
    '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--start-maximized')

driver = webdriver.Chrome(options=chrome_options)

# Hide webdriver flag
driver.execute_cdp_cmd('Network.setUserAgentOverride', {
    "userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                 'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})
driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
    'source': '''
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        })
    '''
})

try:
    # 1) Go to Gmail
    driver.get("https://mail.google.com")

    # 2) Enter email & click Next
    WebDriverWait(driver, 15).until(
        EC.visibility_of_element_located((By.ID, "identifierId"))
    ).send_keys(email)
    WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.ID, "identifierNext"))
    ).click()

    # 3) Wait for password field & enter password
    pwd = WebDriverWait(driver, 15).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "#password input[type='password']"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", pwd)
    pwd.click()
    time.sleep(0.5)
    pwd.clear()
    pwd.send_keys(password)
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "passwordNext"))
    ).click()

    # 4) Wait for inbox to load
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']"))
    )
    print("Logged in successfully!")

    # 5) Wait for inbox to fully load and stabilize
    time.sleep(1)

    # 6) Process all unread emails
    try:
        # Wait for emails to load and get all unread emails
        unread_emails = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr.zA.zE"))
        )
        print(f"Found {len(unread_emails)} unread emails")

        # Enable keyboard shortcuts if not already enabled
        try:
            # Press '?' to check keyboard shortcuts
            actions = ActionChains(driver)
            actions.send_keys('?')
            actions.perform()
            time.sleep(1)
            
            # Press Escape to close the keyboard shortcuts dialog
            actions = ActionChains(driver)
            actions.send_keys(Keys.ESCAPE)
            actions.perform()
            time.sleep(0.5)
        except Exception as e:
            print("Error enabling keyboard shortcuts:", str(e))

        # Process each email
        for i, email in enumerate(unread_emails):
            try:
                # Unselect previous email if it exists
                if i > 0:
                    try:
                        # Get fresh reference to previous email
                        prev_email = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, f"tr.zA.zE:nth-child({i})"))
                        )
                        prev_checkbox = prev_email.find_element(By.CSS_SELECTOR, "div.oZ-jc.T-Jo.J-J5-Ji[role='checkbox']")
                        prev_checkbox.click()
                        print(f"Unselected email {i}")
                        time.sleep(0.5)
                    except Exception as unselect_error:
                        print(f"Error unselecting previous email: {str(unselect_error)}")

                # Get fresh reference to current email
                current_email = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, f"tr.zA.zE:nth-child({i+1})"))
                )
                
                # Select the email using checkbox
                checkbox = current_email.find_element(By.CSS_SELECTOR, "div.oZ-jc.T-Jo.J-J5-Ji[role='checkbox']")
                checkbox.click()
                print(f"\nSelected email {i+1}")
                time.sleep(0.5)

                # Get the email subject
                subject_element = current_email.find_element(By.CSS_SELECTOR, "span.bqe")
                subject = subject_element.get_attribute("textContent").strip()
                subject = ' '.join(word for word in subject.split() if not word.startswith('[') and not word.endswith(']'))
                print(f"Email subject: {subject}")

                # Get label suggestion from Gemini
                prompt = f"Given this email subject: '{subject}', suggest a single word that best describes the category or label this email should belong to. Only respond with the single word, nothing else."
                response = model.generate_content(prompt)
                suggested_label = response.text.strip()
                print(f"Suggested label: {suggested_label}")

                # Press 'l' to open label menu
                actions = ActionChains(driver)
                actions.send_keys('l')
                actions.perform()
                print("Opened label menu")
                time.sleep(0.5)

                # Type the label name
                actions = ActionChains(driver)
                actions.send_keys(suggested_label)
                actions.perform()
                print("Typed label name")
                time.sleep(0.5)

                # Press down arrow to select the "Create new" option
                actions = ActionChains(driver)
                actions.send_keys(Keys.ARROW_DOWN)
                actions.perform()
                print("Selected 'Create new' option")
                time.sleep(0.5)

                # Press Enter to create the label
                actions = ActionChains(driver)
                actions.send_keys(Keys.ENTER)
                actions.perform()
                print("Created new label")
                time.sleep(0.5)

                # Press Tab 4 times to navigate to Create button
                actions = ActionChains(driver)
                actions.send_keys(Keys.TAB * 4)
                actions.perform()
                print("Navigated to Create button")
                time.sleep(0.5)

                # Press Enter to confirm label creation
                actions = ActionChains(driver)
                actions.send_keys(Keys.ENTER)
                actions.perform()
                print("Confirmed label creation")
                time.sleep(1)

            except Exception as email_error:
                print(f"Error processing email {i+1}: {str(email_error)}")
                continue

    except Exception as e:
        print("Error during email processing:", str(e))

    # 7) Pause so you can see the result
    time.sleep(5)

except TimeoutException as te:
    print("Timeout waiting for element:", te)
    driver.save_screenshot("timeout_error.png")
    print("Saved screenshot: timeout_error.png")
except Exception as e:
    print("Error occurred:", e)
    driver.save_screenshot("error_screenshot.png")
    print("Saved screenshot: error_screenshot.png")
finally:
    driver.quit()
