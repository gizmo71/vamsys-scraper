import atexit
import json
import logging
import re
import selenium.common.exceptions
import sys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromiumService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from seleniumwire import webdriver
from seleniumwire.utils import decode as sw_decode
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType
from time import sleep

from vamsys import config

class ExitHooks(object):
    def __init__(self):
        self.original_excepthook = sys.excepthook
        sys.excepthook = self.excepthook
        atexit.register(self.driver_quit)
    def excepthook(self, exception_type, exception, *args):
        if driver:
            print(f"--- page start --- {driver.current_url}", driver.page_source, '--- page end ---', sep='\n')
        self.original_excepthook(exception_type, exception, args)
    def driver_quit(self):
        driver.quit()

logging.basicConfig(stream=sys.stdout)
logging.getLogger("selenium").setLevel(logging.DEBUG)

options = Options()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox") # Only needed to run as root
driver_manager = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
driver = webdriver.Chrome(service=ChromiumService(driver_manager), options=options, seleniumwire_options={'request_storage': 'memory'})
driver.scopes = [ '.*/api/v1/.*' ]

ExitHooks()

driver.get("https://vamsys.io/login")

username_box = WebDriverWait(driver, 30).until(lambda d: d.find_element(by=By.ID, value="email"))
password_box = driver.find_element(by=By.ID, value="password")
remember_me_checkbox = driver.find_element(by=By.ID, value="remember-me")
sign_in_button = driver.find_element(by=By.XPATH, value="//div/button[@type='submit' and normalize-space()='Sign in']")

username_box.send_keys(config["username"])
password_box.send_keys(config["password"])
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
            airline = json.loads(body)
        if request.url == 'https://vamsys.io/api/v1/destinations/map':
            map = json.loads(body)
    return {'airline':airline, 'map':map} if airline and map else None

def handle_dashboard(driver):
    for request in filter(lambda req: req.response, driver.requests):
        body = sw_decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity'))
        body = body.decode("utf-8")
        if request.url == 'https://vamsys.io/api/v1/dashboard':
            return json.loads(body)
    return None

all_data = []

# Or something from https://seleniumhq.github.io/selenium/docs/api/py/webdriver_support/selenium.webdriver.support.expected_conditions.html?highlight=expected
pilot_id_elements = WebDriverWait(driver, 30).until(lambda d: d.find_elements(by=By.XPATH, value="//div[.//p[text()='PIREPs Filed']]/dl/dd/div/button[./i[@class='fal fa-plane-departure']]"))
for pilot_id in list(map(lambda e: e.text, pilot_id_elements)): # Convert to a list so it doesn't hang onto the elements for too long.
    del driver.requests

    print(pilot_id)
    xpath = f"//button[normalize-space() = '{pilot_id}']//ancestor::div[2]"
    pilot_id_element = WebDriverWait(driver, 30).until(lambda d: d.find_element(by=By.XPATH, value=xpath))
    driver.execute_script("arguments[0].scrollIntoView();", pilot_id_element)
    pilot_id_element.click()

    dashboard_rank = WebDriverWait(driver, 30).until(lambda d: d.find_element(by=By.XPATH, value="//div[@class = 'row stats']")).get_attribute('outerHTML')
    dashboard_json = WebDriverWait(driver, 30).until(handle_dashboard)

    sleep(3)
    driver.get("https://vamsys.io/destinations")
    airline_and_map = WebDriverWait(driver, 30).until(handle_destinations)
    airline_and_map['dashboard_rank'] = dashboard_rank
    airline_and_map['dashboard'] = dashboard_json

    sleep(3)
    driver.get("https://vamsys.io/documents/ranks")
    airline_and_map['ranks_html'] = WebDriverWait(driver, 30).until(lambda d: d.find_element(by=By.XPATH, value="//div[@id = 'app']")).get_attribute('outerHTML')

    all_data.append(airline_and_map)
    sleep(3)
    driver.get("https://vamsys.io/select") # Back to the airline selection page for the next airline.

with open(f'vamsys.json', 'w', encoding="utf-8") as f:
    json.dump(all_data, f, indent=4)
