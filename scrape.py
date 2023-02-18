from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromiumService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType
from time import sleep
import atexit

driver = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
driver = webdriver.Chrome(service=ChromiumService(driver))

def driver_quit(): driver.quit()
atexit.register(driver_quit)

driver.get("https://vamsys.io/login")
driver.implicitly_wait(1) #TODO: wait until one or all of the login elements below are found. Consider slowing the script down so it looks less like the bot it actually is...

username_box = driver.find_element(by=By.ID, value="email")
password_box = driver.find_element(by=By.ID, value="password")
sign_in_button = driver.find_element(by=By.CSS_SELECTOR, value="button")

username_box.send_keys("vamsys@davegymer.org")
password_box.send_keys("fcb")
sign_in_button.click()

sleep(2)

# Or something from https://seleniumhq.github.io/selenium/docs/api/py/webdriver_support/selenium.webdriver.support.expected_conditions.html?highlight=expected
pilot_id_elements = WebDriverWait(driver, 2).until(lambda d: d.find_elements(by=By.XPATH, value="//div[.//p[text()='PIREPs Filed']]/dl/dd/div/button[./i[@class='fal fa-plane-departure']]"))
for pilot_id in reversed(list(map(lambda e: e.text, pilot_id_elements))): # Convert to a list so it doesn't hang onto the elements for too long.
    #print(pilot_id)
    xpath = f"//button[normalize-space() = '{pilot_id}']//ancestor::div[2]"
    print(xpath)
    pilot_id_element = WebDriverWait(driver, 2).until(lambda d: d.find_element(by=By.XPATH, value=xpath))
    driver.execute_script("arguments[0].scrollIntoView();", pilot_id_element) # Seems to scroll it too far up - is it the wrong element to do this to? Perhaps just run the "login(nnn)" javascript directly?
    pilot_id_element.click()

    sleep(2)
    driver.get("https://vamsys.io/select") # Back to the airline selection page for the next airline.
