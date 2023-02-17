from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromiumService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType

driverManager = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM)
driver = driverManager.install()
service = ChromiumService(driver)
driver = webdriver.Chrome(service)
