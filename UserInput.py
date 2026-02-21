import logging
import time
import re

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

import model as mo

logger = logging.getLogger(__name__)


def to_csv(df):
    with open('new_cars.csv', 'w', encoding='utf-8', newline="") as cw:
        df.to_csv(cw, sep=',', index=False, encoding='utf-8')


def process_string(input_string):
    result = re.sub(r'\b\d+\s*STR\b', '', input_string)
    result = re.sub(r'\d+(\.\d+)?L?', '', result)

    strings_to_remove = ['petrol', 'diesel', 'cng', 'lpg']
    for string in strings_to_remove:
        result = re.sub(fr'\b{re.escape(string)}\b', '', result, flags=re.IGNORECASE)

    result = re.sub(r'\s+', ' ', result).strip()
    return result


def scroll(driver):
    while True:
        last_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(10)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break


def scrape(car, driver):
    data_list = []
    target_strings = ['Make Year', 'Engine Capacity', 'Transmission', 'KM Driven', 'Ownership', 'Fuel Type']

    try:
        similar_search = driver.find_element(By.CLASS_NAME, "_3fgAP")
        driver.execute_script("arguments[0].scrollIntoView();", similar_search)
    except Exception:
        scroll(driver)

    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(5)
    results_div = driver.find_element(By.CLASS_NAME, '_2ujGx')
    results = results_div.find_elements(By.CLASS_NAME, '_2z-Yu')

    i = 0

    for result in results:
        result_title = result.find_element(By.CLASS_NAME, "_2lmIw")
        if str(car['Year']) in result_title.text:
            try:
                loc = result.find_element(By.CLASS_NAME, "_3DYbK").text.split(",")[-1]
            except Exception:
                loc = None

            result.click()
            driver.switch_to.window(driver.window_handles[1])
            driver.refresh()

            name = driver.find_element(By.CLASS_NAME, '_2Ximl').text
            car_model = driver.find_element(By.CLASS_NAME, '_2UHEW')
            car_model = car_model.find_element(By.CSS_SELECTOR, 'li').text
            name = name + " " + process_string(car_model)

            attr = driver.find_elements(By.CLASS_NAME, 'media-body')
            attr_list = []
            for a in attr:
                aa = a.text.split('\n')
                for aaa in aa:
                    attr_list.append(aaa)

            extracted_data = {}
            for item in target_strings:
                if item in attr_list:
                    key = item
                    if key == 'Make Year':
                        extracted_data[key] = int(attr_list[attr_list.index(item) + 1])
                    elif key == 'Engine Capacity':
                        extracted_data[key] = int(attr_list[attr_list.index(item) + 1].replace(",", "").replace(" cc", ""))
                    elif key == 'KM Driven':
                        extracted_data[key] = int(attr_list[attr_list.index(item) + 1].replace(",", "").replace(" km", ""))
                    elif key == 'Ownership':
                        extracted_data[key] = attr_list[attr_list.index(item) + 1][0]
                    else:
                        extracted_data[key] = attr_list[attr_list.index(item) + 1]
                else:
                    extracted_data[item] = None

            try:
                elements = driver.find_elements(By.CLASS_NAME, "_3oIa7")
                element = elements[3]
                driver.execute_script("arguments[0].scrollIntoView();", element)
                ul = element.find_element(By.CLASS_NAME, '_30qlY')
                li = ul.find_elements(By.CSS_SELECTOR, "li")
                seats = int(li[2].find_element(By.CSS_SELECTOR, "strong").text)
                power = int(li[3].find_element(By.CSS_SELECTOR, "strong").text)
            except Exception:
                seats = None
                power = None

            price_card = driver.find_element(By.CLASS_NAME, 'd-flex.align-items-center')
            price = price_card.find_element(By.CLASS_NAME, '_3i9_p').text
            price = int(float(re.search(r'(\d+(?:\.\d+)?)', price).group(1)) * 100000)

            data_list.append({
                'Location': loc,
                'Year': extracted_data['Make Year'],
                'Kilometers_Driven': extracted_data['KM Driven'],
                'Fuel_Type': extracted_data['Fuel Type'],
                'Transmission': extracted_data['Transmission'],
                'Owner_Type': extracted_data['Ownership'],
                'Engine': extracted_data['Engine Capacity'],
                'Power': power,
                'Price': price,
                'Seats': seats,
                'Name': name,
            })
            i += 1
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            if i == 50:
                break

    df = pd.DataFrame(data_list)
    to_csv(df)
    return df


def web_scrape(item, driver):
    link = "https://www.cars24.com/buy-used-car/"
    driver.get(link)
    driver.implicitly_wait(15)

    search_bars = driver.find_elements(By.CLASS_NAME, "form-control")
    i = search_bars[0]
    i.send_keys(item['Brand'] + " " + item['Model'].split(" ")[0])
    time.sleep(3)

    car_label_ul = driver.find_element(By.CLASS_NAME, "_23UFe")
    car_label_div = car_label_ul.find_element(By.CLASS_NAME, "_2dra0")
    car_label = car_label_div.find_element(By.CSS_SELECTOR, "label")

    time.sleep(2)
    if car_label.find_element(By.CSS_SELECTOR, "span").text == "(0)":
        logger.warning("No cars available for search query")
    else:
        car_label.click()
        time.sleep(2)
        filter_ele = driver.find_elements(By.CLASS_NAME, "_2rOOU")
        fuel_ele = filter_ele[1]
        fuel_ele.click()
        time.sleep(2)
        trans_ele = filter_ele[6]
        trans_ele.click()
        time.sleep(2)

        ul = driver.find_elements(By.CLASS_NAME, "_23UFe.WGG8F")

        fuel_ul = ul[0]
        fuel_labels = fuel_ul.find_elements(By.CSS_SELECTOR, "label")
        fuel_type = item['Fuel_Type']
        fuels = ""
        for f in fuel_labels:
            fuels = fuels + f.text[0]
        if "cng" in fuel_type.lower():
            cng = fuel_labels[fuels.index('C')]
            cng.click()
            time.sleep(1)
        if "petrol" in fuel_type.lower():
            petrol = fuel_labels[fuels.index('P')]
            petrol.click()
            time.sleep(1)
        if "diesel" in fuel_type.lower():
            diesel = fuel_labels[fuels.index('D')]
            diesel.click()
            time.sleep(1)
        if "lpg" in fuel_type.lower():
            lpg = fuel_labels[fuels.index('L')]
            lpg.click()
            time.sleep(1)

        trans_ul = ul[1]
        trans_labels = trans_ul.find_elements(By.CSS_SELECTOR, "label")
        trans_type = item['Transmission']
        trans = ""
        for t in trans_labels:
            trans = trans + t.text[0]
        if "automatic" in trans_type.lower():
            automatic = trans_labels[trans.index('A')]
            automatic.click()
            time.sleep(0.2)
        if "manual" in trans_type.lower():
            manual = trans_labels[trans.index('M')]
            manual.click()
            time.sleep(0.2)

        df = scrape(item, driver)

    return df


def ui_scrape(car_details, driver):
    start_time = time.time()
    df = web_scrape(car_details, driver)
    price = mo.model_call(df, car_details)
    elapsed_time = time.time() - start_time
    logger.info("Scraping completed in %.1f secs (%.1f mins)", elapsed_time, elapsed_time / 60)
    driver.quit()
    return int(price)


def start_driver():
    driver = webdriver.Firefox()
    ActionChains(driver)
    driver.minimize_window()
    driver.maximize_window()
    return driver
