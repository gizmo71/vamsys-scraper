import atexit
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromiumService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType
from seleniumwire import webdriver
from seleniumwire.utils import decode as sw_decode
from time import sleep

driver_manager = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
driver = webdriver.Chrome(service=ChromiumService(driver_manager), seleniumwire_options={'request_storage': 'memory'})
driver.scopes = [ '.*/api/v1/.*' ]

def driver_quit(): driver.quit()
atexit.register(driver_quit)

driver.get("https://vamsys.io/login")
driver.implicitly_wait(1) #TODO: wait until one or all of the login elements below are found. Consider slowing the script down so it looks less like the bot it actually is...

username_box = driver.find_element(by=By.ID, value="email")
password_box = driver.find_element(by=By.ID, value="password")
remember_me_checkbox = driver.find_element(by=By.ID, value="remember-me")
sign_in_button = driver.find_element(by=By.CSS_SELECTOR, value="button")

username_box.send_keys("vamsys@davegymer.org")
password_box.send_keys("fcb")
remember_me_checkbox.click()
sign_in_button.click()

sleep(2)

def handle_destinations(driver):
    airline = None
    map = None
    for request in filter(lambda req: req.response, driver.requests):
        body = sw_decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity'))
        body = body.decode("utf-8")
        if request.url == 'https://vamsys.io/api/v1/airline':
            airline = body
        if request.url == 'https://vamsys.io/api/v1/destinations/map':
            map = body
    return '{\n"airline":%s,\n"map":%s\n}' % (airline, map) if airline and map else None

all_data = []

# Or something from https://seleniumhq.github.io/selenium/docs/api/py/webdriver_support/selenium.webdriver.support.expected_conditions.html?highlight=expected
pilot_id_elements = WebDriverWait(driver, 5).until(lambda d: d.find_elements(by=By.XPATH, value="//div[.//p[text()='PIREPs Filed']]/dl/dd/div/button[./i[@class='fal fa-plane-departure']]"))
for pilot_id in list(map(lambda e: e.text, pilot_id_elements)): # Convert to a list so it doesn't hang onto the elements for too long.
    print(pilot_id)
    xpath = f"//button[normalize-space() = '{pilot_id}']//ancestor::div[2]"
    pilot_id_element = WebDriverWait(driver, 10).until(lambda d: d.find_element(by=By.XPATH, value=xpath))
    driver.execute_script("arguments[0].scrollIntoView();", pilot_id_element) # Seems to scroll it too far up - is it the wrong element to do this to? Perhaps just run the "login(nnn)" javascript directly?
    pilot_id_element.click()

    sleep(5)
    del driver.requests
    driver.get("https://vamsys.io/destinations")
    airline_and_map = WebDriverWait(driver, 15).until(handle_destinations)
    all_data.append(json.loads(airline_and_map))

    sleep(5)
    driver.get("https://vamsys.io/select") # Back to the airline selection page for the next airline.

with open(f'vamsys.json', 'w', encoding="utf-8") as f:
    json.dump(all_data, f, indent=4)
