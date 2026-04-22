from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import requests
import pandas as pd
from openpyxl import load_workbook
import time

HEADLESS = False
TIMEFORCAPCHA = 15

def log_in():
    try:
        with open('user.txt', 'r') as f:
            content = f.readlines()
        user_login = content[0].strip()
        user_password = content[1].strip()
        if not user_login or not user_password:
            exit()
        return user_login, user_password
    except Exception as e:
        print(f'Error in log_in(): {e}')
        exit()

def open_driver():
    options = Options()
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')
    if HEADLESS:
        options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    return driver

def get_cookies(driver, user_login, user_password):
    try:
        driver.get('https://encoreiset.fitbase.io')
        time.sleep(1)
        driver.find_element(By.ID, 'loginform-username').send_keys(user_login)
        driver.find_element(By.ID, 'loginform-password').send_keys(user_password)
        time.sleep(TIMEFORCAPCHA)
        driver.find_element(By.XPATH, '//*[@id="login-form"]/button').click()
        time.sleep(1)
        return driver.get_cookies()
    except Exception as e:
        print(f'Error in get_cookies(): {e}')
        exit()

def get_last_client_id(driver, cookies):
    for cookie in cookies:
        driver.add_cookie(cookie)
        # print(f'{cookie}')
    driver.refresh()
    print('driver.refresh')
    driver.get('https://encoreiset.fitbase.io/clients')
    print('driver.get')
    try:
        last_client = driver.find_element(By.XPATH, '//*[@id="example-container"]/table/tbody/tr[1]/td[1]/input').get_attribute('value')
        print(f"Количество клиентов: {last_client}")
        return int(last_client)
    except Exception as e:
        print(f'Error in get_last_client_id(): {e}')
        exit()
    finally:
        driver.quit()

def fetch(url, cookies, retries=3):
    for i in range(retries):
        try:
            session = requests.Session()
            session.cookies.update({cookie['name']: cookie['value'] for cookie in cookies})
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
                'X-Requested-With': 'XMLHttpRequest'
            }
            response = session.get(url, headers=headers, timeout=30)
            return response.text
        except Exception as e:
            print(f'Error in fetch(): {e}')
            if i == retries - 1:
                print(f"Ошибка при запросе к {url}: {e}")
                return None
            time.sleep(2 ** i)

def process_client(client_id, cookies):
    data = []
    url = f'https://encoreiset.fitbase.io/clients/view?id={client_id}'
    response = fetch(url, cookies)
    if not response:
        return data

    bs = BeautifulSoup(response, "lxml")
    name = bs.find('h1', 'client_name').text.strip() if bs.find('h1', 'client_name') else ''
    try:
        # contract_id = bs.find_all('div', id=lambda x: x and x.startswith('contract_item-'))
        # card_code = contract_id[0]['id'].split('-')[1]
        # for i in range(0, len(contract_id)-1):
        #     a = contract_id[i][id].split(' - ')[1]
        #     print(f'{i}: {a}')

        # contract_id = bs.find_all('div', 'contract_item-id')
        # print(contract_id)
        # card_code = contract_id[0].text.replace('#', '')

        contract_id = bs.find_all('div', id=lambda x: x and x.startswith('contract_item-'))
        card_code = contract_id[0]['id'].split('-')[1]

    except:
        card_code = 'Активный абонемент отсутствует'

    services_url = f'https://encoreiset.fitbase.io/clients/view-client-services?client_id={client_id}'
    services_response = fetch(services_url, cookies)
    if not services_response:
        return data

    bs_services = BeautifulSoup(services_response, "lxml")
    try:
        pagination = bs_services.find('div', 'pagination-summary')
        time.sleep(0.5)
        pagination = pagination.text.rstrip().split(' ')[-1]
        pagination = int(pagination) // 10 + 1
    except:
        return data

    pages = []
    for page in range(1, pagination+1):
        pages.append(page)
    if not pages:
        return data

    services = []
    for page in pages:
        page_url = f'https://encoreiset.fitbase.io/clients/view-client-services?client_id={client_id}&ClientServicesSearch%5BshowActive%5D=0&ClientServicesSearch%5BshowUnpaid%5D=0&_pjax=%23client_services-pjax-{client_id}&services-page={page}&per-page=10'
        page_response = fetch(page_url, cookies)
        if page_response:
            bs_page = BeautifulSoup(page_response, "lxml")
            table = bs_page.find('table', 'table table-bordered')
            if table:
                for row in table.find_all('tr', id=lambda x: x and x.startswith('service_item-id-')):
                    tds = row.find_all('td')
                    if len(tds) >= 6:
                        date_td = tds[-2]
                        date_text = date_td.text.strip().replace(')', '')
                        if date_text:
                            try:
                                year = int(date_text.split('.')[-1].rstrip())
                                if year >= 2026:
                                    service_id = row['id'].split('-')[2]
                                    services.append(service_id)
                            except ValueError:
                                continue


    for service in services:
        service_url = f'https://encoreiset.fitbase.io/clients/serv-stat?id={service}'
        service_response = fetch(service_url, cookies)
        if not service_response:
            continue

        bs_service = BeautifulSoup(service_response, "lxml")
        table1 = bs_service.find('table', 'table table-hover table-bordered sortable dataTable no-footer')
        if not table1:
            continue

        tds = table1.find_all('td')

        end_service = tds[7].text.split(' ')[0] if tds[7].text.split(' ')[0] != '-' else ''
        if not end_service or int(end_service.split('.')[2]) >= 2026:
            # print(end_service)
            name_service = tds[0].text
            try:
                price_service = tds[2].text.split(',')[0]
                price_service = price_service.replace(' ', '')
            except:
                price_service = ''
            payment_date = tds[5].text.split(' ')[0] if tds[5].text.split(' ')[0] != '-' else ''
            start_service = tds[6].text.split(' ')[0] if tds[6].text.split(' ')[0] != 'Не' else ''
            table2 = bs_service.find('table', 'kv-grid-table table table-bordered table-striped')
            if not table2:
                data.append([name, client_id, name_service, payment_date, start_service, end_service, None, price_service])
                continue

            for row in table2.find('tbody').find_all('tr'):
                tds = row.find_all('td')
                if tds[0].text == 'Ничего не найдено.':
                    activation_date = ''
                else:
                    activation_date = tds[1].text.split(' ')[0]

                data.append([name,              # ФИО
                             client_id,         # id клиента
                             card_code,         # код абонемента
                             name_service,      # название услуги
                             payment_date,      # дата оплаты
                             start_service,     # начало действия услуги
                             end_service,       # конец действия
                             activation_date,   # дата активации
                             price_service])    # стоимость

                print([name, client_id, card_code, name_service, payment_date, start_service, end_service, activation_date, price_service])

    print(f'Клиент {client_id} обработан')
    return data

def main():

    start_time = time.time()
    print('Старт')
    user_login, user_password = log_in()
    print('user_login, user_password')
    driver = open_driver()
    print('driver')
    cookies = get_cookies(driver, user_login, user_password)
    print('cookies')
    last_client = get_last_client_id(driver, cookies)
    print('last_client')

    # first_user, last_user = 1, last_client
    first_user, last_user = 1, 9
    
    
    all_data = []
    for client_id in range(first_user, last_user + 1):
        print(f'Обработка клиента {client_id}')
        client_data = process_client(client_id, cookies)
        all_data.extend(client_data)

    if all_data:
        columns = ['ФИО', 
                   'ID клиента', 
                   'Код (номер) первого активного абонемента', 
                   'Название', 
                   'Дата оплаты', 
                   'Начало действия', 
                   'Окончание действия', 
                   'Дата активации', 
                   'Стоимость']
        df = pd.DataFrame(all_data, columns=columns)
        df['Стоимость'] = df['Стоимость'].astype(int)

        output_file = f'services ({first_user}-{last_user}).xlsx'
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)

        workbook = load_workbook(output_file)
        sheet = workbook.active
        for column in sheet.columns:
            max_length = max(len(str(cell.value)) for cell in column if cell.value) + 2
            sheet.column_dimensions[column[0].column_letter].width = max_length
        workbook.save(output_file)

    end_time = time.time()
    print(f'Время выполнения: {round((end_time - start_time)/3600, 1)} часов')

if __name__ == "__main__":
    main()