from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
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
model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')

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

    # 6) Find and drag first email to first label
    try:
        # Wait for and get fresh references to elements
        first_email = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tr.zA.zE"))
        )

        # Get the email subject
        subject_element = first_email.find_element(By.CSS_SELECTOR, "span.bqe")
        # Get the text content and clean it up
        subject = subject_element.get_attribute("textContent").strip()
        # Remove any emoji or special characters
        subject = ' '.join(word for word in subject.split() if not word.startswith('[') and not word.endswith(']'))
        print(f"Email subject: {subject}")

        # Get label suggestion from Gemini
        prompt = f"Given this email subject: '{subject}', suggest a single word that best describes the category or label this email should belong to. Only respond with the single word, nothing else."
        response = model.generate_content(prompt)
        suggested_label = response.text.strip()
        print(f"Suggested label: {suggested_label}")

        # Get fresh references right before the drag operation
        first_email = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tr.zA.zE"))
        )
        first_label = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.TN.aY7xie.aEc.aHS-bnr"))
        )

        # Scroll elements into view
        driver.execute_script("arguments[0].scrollIntoView(true);", first_email)
        driver.execute_script("arguments[0].scrollIntoView(true);", first_label)
        time.sleep(0.1)

        # Perform drag and drop with fresh element references
        actions = ActionChains(driver)
        actions.move_to_element(first_email)
        actions.pause(0.1)
        actions.click_and_hold()
        actions.pause(0.1)
        actions.move_to_element(first_label)
        actions.pause(0.1)
        actions.release()
        actions.perform()
        print("Dragged email to label!")

        # Wait for the page to stabilize
        time.sleep(0.5)

        # Click into the label
        try:
            label_to_click = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.TN.aY7xie.aEc.aHS-bnr"))
            )
            label_to_click.click()
            print("Clicked into label!")

            # Wait for the page to stabilize after clicking the label
            time.sleep(0.5)

            # Drag email back to inbox
            try:
                # Wait for the inbox to be present and get a fresh reference
                inbox = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.TN.bzz.aHS-bnt"))
                )
                
                # Wait for the email list to be present and get a fresh reference
                email_list = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']"))
                )
                
                # Get a fresh reference to the first email
                email_to_drag = WebDriverWait(email_list, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tr.zA.zE"))
                )

                # Scroll elements into view
                driver.execute_script("arguments[0].scrollIntoView(true);", email_to_drag)
                driver.execute_script("arguments[0].scrollIntoView(true);", inbox)
                time.sleep(0.1)

                # Perform drag and drop back to inbox
                actions = ActionChains(driver)
                actions.move_to_element(email_to_drag)
                actions.pause(0.1)
                actions.click_and_hold()
                actions.pause(0.1)
                actions.move_to_element(inbox)
                actions.pause(0.1)
                actions.release()
                actions.perform()
                print("Dragged email back to inbox!")

            except Exception as drag_back_error:
                print("Error dragging back to inbox:", str(drag_back_error))

        except Exception as click_error:
            print("Error clicking into label:", str(click_error))

    except Exception as e:
        print("Error during drag and drop:", str(e))

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
