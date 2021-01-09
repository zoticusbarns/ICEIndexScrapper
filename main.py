import os
import selenium
from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
import pickle
import logging
from PIL import Image
import io
import time

logger = logging.getLogger()


def save_element_screen(element, newfilename):
    Path(os.path.dirname(newfilename)).mkdir(parents=True, exist_ok=True)
    img_bytes = element.screenshot_as_png
    image_stream = io.BytesIO(img_bytes)
    img = Image.open(image_stream)
    img.save(newfilename)


def init_driver(driver_path):
    logger.info("Starting browser...")
    # Config options for Chrome
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument("--test-type")

    # Init Chrome Driver and negivate to target page
    driver = Chrome(executable_path=driver_path, options=options)
    driver.maximize_window()
    return driver


def login(driver, user_id):
    logger.info("Logging in")
    cookies_loaded = False
    try:
        cookies = pickle.load(open("cookies.pkl", "rb"))
        logger.info("Loaded cookies")
        for cookie in cookies:
            driver.add_cookie(cookie)
        cookies_loaded = True
    except FileNotFoundError:
        pass
    time.sleep(1)

    password = input("Please enter password: ")
    user_id_element = driver.find_element_by_xpath("//div[@id='loginTemplate']//input[@name='user']")
    user_id_element.send_keys(user_id)
    password_element = driver.find_element_by_xpath("//div[@id='loginTemplate']//input[@name='password']")
    password_element.send_keys(password)

    login_element = driver.find_element_by_xpath("//button[@name='loginPageSubmitBtn']")
    login_element.click()
    time.sleep(1)

    try:
        f2a_element = driver.find_element_by_xpath("//div[@id='loginTemplate']//input[@name='otpCode']")
        emailF2A = input("Please enter F2A: ")
        f2a_element.send_keys(emailF2A)
        login_element.click()
    except selenium.common.exceptions.NoSuchElementException:
        pass

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//input[@class='ice-text-input css-1d4783a']"))
    )
    if not cookies_loaded:
        pickle.dump(driver.get_cookies(), open("cookies.pkl", "wb"))

    logger.info("Logged in successfully")


def get_index(driver, index: str, date: str, results: list):
    index_input = driver.find_element_by_xpath("//input[@class='ice-text-input css-1d4783a']")
    index_input.send_keys(Keys.CONTROL + 'a')
    index_input.send_keys(Keys.DELETE)
    index_input.send_keys(index)

    date_input = driver.find_element_by_xpath("//input[@class='ice-text-input css-xfoevw']")
    date_input.send_keys(Keys.CONTROL + 'a')
    date_input.send_keys(Keys.DELETE)
    date_input.send_keys(date)
    date_input.send_keys(Keys.ENTER)
    time.sleep(1)

    index_snapshot_element = driver.find_element_by_xpath("//div[@class='homeSnapshot css-oo7x0w']")
    index_detail = driver.find_element_by_xpath("//div[@class='homeSnapshot css-oo7x0w']"
                                                "//div[@class='indexDetail']/div[@class='detail']")

    count = 0
    while count < 500:
        index_detail = driver.find_element_by_xpath("//div[@class='homeSnapshot css-oo7x0w']"
                                                    "//div[@class='indexDetail']/div[@class='detail']")
        if index in index_detail.get_attribute("innerHTML") and date in index_detail.get_attribute("innerHTML"):
            try:
                driver.find_element_by_xpath("//div[text()='Loading...']")
            except selenium.common.exceptions.NoSuchElementException:
                break
        count += 1
    else:
        return False

    oas_govt_element = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located(
            (By.XPATH,
             "//div[@class='homeSnapshot css-oo7x0w']"
             "//div[@class='ag-center-cols-container']"
             "//div[@row-id='2']//div[@col-id='V4']")
        )
    )
    index_detail = driver.find_element_by_xpath("//div[@class='homeSnapshot css-oo7x0w']"
                                                "//div[@class='indexDetail']/div[@class='detail']")
    if not (index in index_detail.get_attribute("innerHTML") and date in index_detail.get_attribute("innerHTML")):
        return False
    try:
        if int(oas_govt_element.get_attribute("innerHTML")) == results[-1][1]:
            return False
    except IndexError:
        pass

    results.append(
        (index, int(oas_govt_element.get_attribute("innerHTML")))
    )
    date = date.replace("/", "-")
    save_element_screen(index_snapshot_element, f"screensave/{date}/{index}.png")
    time.sleep(1)

    return True


def read_index_list(path):
    with open(path, 'r') as f:
        lines = f.readlines()
    index_list = lines[0].split(",")
    index_list[0] = index_list[0].replace("ï»¿", "")
    index_list[-1] = index_list[-1].replace("\n", "")
    return index_list


def write_results_to_csv(results, directory, page, date):
    date = date.replace("/", "-")
    if directory == "":
        filename = f"ice_oas_govt {date}.csv"
    else:
        filename = f"{directory}\\ice_oas_govt {date}.csv"

    logger.info(f"Writing collected data to csv: {filename}")
    with open(filename, 'w') as f:
        f.write(f"Source,{page}\n")
        f.write(f"As of {date}\n\n")
        f.write("Index,Yield\n")
        for data in results:
            f.write(f"{data[0]},{data[1]}\n")


def main(driver_path: str, date: str, user_id: str):
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info("Starting Script")

    driver = init_driver(driver_path)
    page = "https://indices.theice.com/home"
    logger.info(f"Loading page {page}")
    driver.get(page)
    logger.info("Page loaded successfully")

    login(driver=driver, user_id=user_id)

    results = []
    index_list = read_index_list("index_list.csv")
    for i, index in enumerate(index_list):
        max_tries = 5
        flag = get_index(driver, index, date, results)
        retry = 0
        while not flag and max_tries > 0:
            retry += 1
            logger.warning(f"Failed to load index {index} as of {date}, retry ({retry})")
            flag = get_index(driver, index, date, results)
            max_tries -= 1

        if not flag:
            raise Exception("Failed to load data within max number of retry")

        logger.info(f"Index {index} as of {date} loaded successfully. {i+1}/{len(index_list)} completed")

    logger.info(f"Data collected for {len(results)} index")

    write_results_to_csv(results, "", page, date)
    driver.close()


if __name__ == '__main__':
    import timeit
    start = timeit.default_timer()

    date = "09/30/2020"  # valuation date in the format of mm/dd/yyyy
    path = ""  # Path to Chrome web driver
    user_id = ""  # login user name

    main(path, date)

    stop = timeit.default_timer()
    print('Time: ', (stop - start) / 60, "mins")

