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
import json
import asyncio
from websocket_manager import broadcast_status

# Load credentials
load_dotenv()

def run_gmail_automation(headless: bool = False):
    email = os.getenv("GMAIL_EMAIL")
    password = os.getenv("GMAIL_PASSWORD")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    # Configure Gemini
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')

    # Chrome "stealth" options
    chrome_options = Options()
    chrome_options.add_argument('--headless=new') if headless else None
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
        asyncio.run(broadcast_status("Initialization begin", "info"))

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
        asyncio.run(broadcast_status("Successfully initialized", "success"))

        # 5) Wait for inbox to fully load and stabilize
        time.sleep(1)

        # 6) Process all unread emails
        try:
            # Wait for emails to load and get all unread emails
            unread_emails = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "tr.zA.zE"))
            )
            asyncio.run(broadcast_status(f"Found {len(unread_emails)} unread emails to process", "info"))

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
                asyncio.run(broadcast_status(f"Error enabling keyboard shortcuts: {str(e)}", "warning"))

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
                            time.sleep(0.5)
                        except Exception as unselect_error:
                            asyncio.run(broadcast_status(f"Error unselecting previous email: {str(unselect_error)}", "warning"))

                    # Get fresh reference to current email
                    current_email = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, f"tr.zA.zE:nth-child({i+1})"))
                    )
                    
                    # Select the email using checkbox
                    checkbox = current_email.find_element(By.CSS_SELECTOR, "div.oZ-jc.T-Jo.J-J5-Ji[role='checkbox']")
                    checkbox.click()
                    time.sleep(0.5)

                    # Get the email subject
                    subject_element = current_email.find_element(By.CSS_SELECTOR, "span.bqe")
                    subject = subject_element.get_attribute("textContent").strip()
                    subject = ' '.join(word for word in subject.split() if not word.startswith('[') and not word.endswith(']'))
                    asyncio.run(broadcast_status(f"Processing email {i+1}: {subject}", "info"))

                    # Get label suggestion from Gemini
                    prompt = f"Given this email subject: '{subject}', suggest a single word that best describes the category or label this email should belong to. Only respond with the single word, nothing else."
                    response = model.generate_content(prompt)
                    suggested_label = response.text.strip()
                    asyncio.run(broadcast_status(f"Suggested label: {suggested_label}", "info"))

                    # Press 'l' to open label menu
                    actions = ActionChains(driver)
                    actions.send_keys('l')
                    actions.perform()
                    time.sleep(0.5)

                    # Type the label name
                    actions = ActionChains(driver)
                    actions.send_keys(suggested_label)
                    actions.perform()
                    time.sleep(0.5)

                    # Press down arrow to select the "Create new" option
                    actions = ActionChains(driver)
                    actions.send_keys(Keys.ARROW_DOWN)
                    actions.perform()
                    time.sleep(0.5)

                    # Press Enter to create the label
                    actions = ActionChains(driver)
                    actions.send_keys(Keys.ENTER)
                    actions.perform()
                    time.sleep(0.5)

                    # Press Tab 4 times to navigate to Create button
                    actions = ActionChains(driver)
                    actions.send_keys(Keys.TAB * 4)
                    actions.perform()
                    time.sleep(0.5)

                    # Press Enter to confirm label creation
                    actions = ActionChains(driver)
                    actions.send_keys(Keys.ENTER)
                    actions.perform()
                    asyncio.run(broadcast_status(f"Created and applied label '{suggested_label}' to email: {subject}", "success"))
                    time.sleep(1)

                except Exception as email_error:
                    asyncio.run(broadcast_status(f"Error processing email {i+1}: {str(email_error)}", "error"))
                    continue

        except Exception as e:
            asyncio.run(broadcast_status(f"Error during email processing: {str(e)}", "error"))

        # 7) Pause so you can see the result
        time.sleep(1)
        asyncio.run(broadcast_status("Gmail automation completed successfully!", "success"))

    except TimeoutException as te:
        asyncio.run(broadcast_status(f"Timeout waiting for element: {str(te)}", "error"))
        driver.save_screenshot("timeout_error.png")
        return {"status": "error", "detail": f"Timeout: {str(te)}"}
    except Exception as e:
        asyncio.run(broadcast_status(f"Error occurred: {str(e)}", "error"))
        driver.save_screenshot("error_screenshot.png")
        return {"status": "error", "detail": str(e)}
    finally:
        driver.quit()
    
    return {"status": "success", "message": "Gmail automation completed successfully", "refresh": True}

if __name__ == "__main__":
    run_gmail_automation()
