import argparse
import atexit
import json
import logging
import re
import selenium.common.exceptions
import sys

from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from seleniumwire import webdriver
from seleniumwire.utils import decode as sw_decode
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from time import sleep

from vamsys import config

parser = argparse.ArgumentParser(description='Scrape route and other data from vAMSYS')
parser.add_argument('pilot_ids', help='Only scrape specific IDs', nargs='*')
args = parser.parse_args()

def decode_body(doc):
    uncompressed = sw_decode(doc.body, doc.headers.get('content-encoding', 'identity'))
    return uncompressed.decode('UTF-8')

class ExitHooks(object):
    def __init__(self):
        self.original_excepthook = sys.excepthook
        sys.excepthook = self.excepthook
        atexit.register(self.driver_quit)
    def excepthook(self, exception_type, exception, *args):
        if driver:
            #TODO: dump just a small bit to stdout and the whole thing to a file
            with open(f'unprocessable.html', 'w', encoding="utf-8") as f:
                f.write(f"<!-- Error processing {driver.current_url} -->\n")
                f.write(driver.page_source)
            for request in filter(lambda req: req.response, driver.requests):
                print(f"\t{request.url} {request.response.headers.get('Content-Encoding', 'none')} {type(request.response.body)} {request.response.headers.get('Content-Type', 'none')}")
        self.original_excepthook(exception_type, exception, args)
    def driver_quit(self):
        driver.quit()

logging.basicConfig(stream=sys.stdout)
#logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logging.DEBUG)

options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox") # Only needed to run as root
options.add_argument('--disable-dev-shm-usage')
service = Service()
driver = webdriver.Firefox(options=options, service=service)
driver.set_page_load_timeout(60)
driver.set_window_size(1280, 768)
driver.scopes = [ r'^https://(?:(?:ws\.auth\.)?vamsys\.io|(?:map|plausible)\.vamsys\.dev)/(?!broadcasting/auth|cdn-cgi/rum)' ]

ExitHooks()

driver.get("https://vamsys.io/login")

username_box = WebDriverWait(driver, 30).until(lambda d: d.find_element(by=By.ID, value="emailaddress"))
password_box = driver.find_element(by=By.ID, value="password")
remember_me_checkbox = driver.find_element(by=By.ID, value="checkbox-signin")
sign_in_button = driver.find_element(by=By.XPATH, value="//div/button[@type='submit' and normalize-space()='Sign In']")

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
        elif request.url == 'https://vamsys.io/api/v1/destinations/map':
            map = json.loads(body)
    return {'airline':airline, 'map':map} if airline and map else None

def handle_pireps(driver):
    for request in filter(lambda req: req.response, driver.requests):
        body = decode_body(request.response)
        if request.url == 'https://vamsys.io/api/v1/pilot/pireps':
            return json.loads(body)

sleep(1)
driver.get("https://vamsys.io/select")

airline_snapshot = WebDriverWait(driver, 30).until(lambda d: d.find_element(by=By.XPATH, value="(//div[./@*[local-name() = 'wire:snapshot' and contains(., 'Dan Air Virtual')]])[1]")).get_attribute('wire:snapshot')
id_to_airline = dict((row[0]['pilot_username'], row[0]) for row in json.loads(airline_snapshot)['data']['airlines'][0])

# Or something from https://seleniumhq.github.io/selenium/docs/api/py/webdriver_support/selenium.webdriver.support.expected_conditions.html?highlight=expected
pilot_id_elements = WebDriverWait(driver, 30).until(lambda d: d.find_elements(by=By.XPATH, value="//button[starts-with(@*, 'login(')]"))
all_pilot_ids = list(map(lambda e: e.text.strip(), pilot_id_elements))
print(*(['All pilot_ids:'] + all_pilot_ids))
pilot_ids = args.pilot_ids or [id for id in all_pilot_ids if id not in ['suppress']]
unknown_ids = set(pilot_ids) - set(all_pilot_ids)
if unknown_ids:
    raise ValueError(f"Unknown airlines: {unknown_ids}; known airlines are {all_pilot_ids}")
print(*(['filtered:'] + pilot_ids))

for pilot_id in pilot_ids:
    del driver.requests
    airline_and_map = {}

    print(pilot_id)
    xpath = f"//button[normalize-space() = '{pilot_id}']"
    pilot_id_element = WebDriverWait(driver, 30).until(lambda d: d.find_element(by=By.XPATH, value=xpath))
    driver.execute_script("arguments[0].click();", pilot_id_element)

    profile_link = WebDriverWait(driver, 60).until(lambda d: d.find_element(by=By.XPATH, value="//li[./a/span[normalize-space() = 'My Profile']]/ul/li/a[./span[normalize-space() = 'Dashboard']]")).get_attribute('href')
    airline_and_map['id'] = re.search(r'https://vamsys.io/phoenix/profile/([A-Z]{3})(\d+)/\1\d+', profile_link).group(2)
    airline_and_map['info'] = id_to_airline[pilot_id]
    sleep(2)
    driver.get(profile_link)
    airline_and_map['profile'] = WebDriverWait(driver, 30).until(lambda d: d.find_element(by=By.XPATH, value="//main/div")).get_attribute('outerHTML')
    # We can grab the latest PIREP even if invalidated for the purposes of block/air time check.
    # We need latest "Accepted" or "Rejected" for non-participation requirements VAs, but(?) must be Accepted for those with "PIREPs per" requirements.
    pirep_link = WebDriverWait(driver, 5).until(lambda d: d.find_element(by=By.XPATH, value="//table[thead/tr/th//span[normalize-space() = 'Status']]/tbody/tr/td//a")).get_attribute('href')
    sleep(1)
    driver.get(pirep_link)
    airline_and_map['latest_pirep'] = WebDriverWait(driver, 30).until(lambda d: d.find_element(by=By.XPATH, value="//div[@class='card' and .//h4[normalize-space() = 'Flight Details']]")).get_attribute('outerHTML')

    del driver.requests # Avoid "wrong" livewire/update calls. But somehow it's getting the PIREP update anyway. Hmm.
    sleep(1)
    driver.get("https://vamsys.io/phoenix/flight-center/destinations")
    airline_and_map['airports'] = driver.page_source #WebDriverWait(driver, 30).until(handle_airports)

    airline_and_map['history'] = []
    for request in driver.requests:
        def json_headers(httpHeaders):
            return [f"{x}: {httpHeaders[x]}" for x in httpHeaders]
        data = {'url':request.url, 'request':{'headers':json_headers(request.headers), 'body':decode_body(request)}}
        if request.response:
            data['response'] = {'headers':json_headers(request.response.headers), 'body':decode_body(request.response)}
        airline_and_map['history'].append(data)

    sleep(2)
    driver.get("https://vamsys.io/phoenix/flight-center/pireps")
    airline_and_map['pireps'] = WebDriverWait(driver, 5).until(lambda d: d.find_element(by=By.XPATH, value="//table")).get_attribute('outerHTML')

    driver.save_screenshot(f"vamsys.{pilot_id}.png")

    with open(f'vamsys.{pilot_id}.json', 'w', encoding="utf-8") as f:
        json.dump(airline_and_map, f, indent=4)
    sleep(1)
    driver.get("https://vamsys.io/select") # Back to the airline selection page for the next airline.
