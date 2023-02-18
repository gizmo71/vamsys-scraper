from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromiumService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType
from time import sleep

driver = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
driver = webdriver.Chrome(service=ChromiumService(driver))

driver.get("https://vamsys.io/login")
driver.implicitly_wait(1)

username_box = driver.find_element(by=By.ID, value="email")
password_box = driver.find_element(by=By.ID, value="password")
sign_in_button = driver.find_element(by=By.CSS_SELECTOR, value="button")

username_box.send_keys("vamsys@davegymer.org")
password_box.send_keys("fcb")
sign_in_button.click()

#sleep(5)

# Or something from https://seleniumhq.github.io/selenium/docs/api/py/webdriver_support/selenium.webdriver.support.expected_conditions.html?highlight=expected
pilotIdElements = WebDriverWait(driver, 5).until(lambda d: d.find_elements(by=By.XPATH, value="//div[.//p[text()='PIREPs Filed']]/dl/dd/div/button[./i[@class='fal fa-plane-departure']]"))
pilotIdIterator = map(lambda pilotIdElement: pilotIdElement.text, pilotIdElements)
for pilotId in pilotIdIterator:
    print(pilotId)

driver.quit()
