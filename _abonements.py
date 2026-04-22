from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import requests
from bs4 import BeautifulSoup
import pandas as pd
from openpyxl import load_workbook
import re
import time
import os


HEADLESS = False
TIMEFORCAPCHA = 15
custom_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
# custom_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36'


def open_driver():
    options = Options()
    options.add_argument(f'--user-agent={custom_user_agent}')
    if HEADLESS:
        options.add_argument('--headless')
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def get_cookie():
    try:
        driver.get(url)
        time.sleep(1)
        driver.implicitly_wait(10)
        username = driver.find_element(By.ID, 'loginform-username').send_keys(user_login)
        password = driver.find_element(By.ID, 'loginform-password').send_keys(user_password)
        time.sleep(TIMEFORCAPCHA)
        login_button = driver.find_element(By.XPATH, '//*[@id="login-form"]/button').click()
        time.sleep(1)
        cookies = driver.get_cookies()
        return cookies

    except Exception as e:
        print(f'Error in get_cookie: {e}')


def add_cookie(cookies):
    for cookie in cookies:
        driver.add_cookie(cookie)
    driver.refresh()
    url_client = f'https://encoreiset.fitbase.io/clients'
    driver.get(url_client)

    try:
        driver.implicitly_wait(3)
        last_client = driver.find_element(By.XPATH,
                                          '''//*[@id="example-container"]/table/tbody/tr[1]/td[1]/input''').get_attribute(
            'value')
        print(f"Количество клиентов: {last_client}")
    except Exception as e:
        print(f'Error in request: {e}')
        exit()
    finally:
        driver.quit()

    for cookie in cookies:
        s.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

    return last_client


def request(client_id):
    try:
        headers = {
            'Content-Type': 'application/json',
            'Referer': f'https://encoreiset.fitbase.io/clients/?clientModal={client_id}',
            'x-requested-with': 'XMLHttpRequest'
        }
        response = s.get(f'''https://encoreiset.fitbase.io/clients/view?id={client_id}''', headers=headers)
        bs = BeautifulSoup(response.text, "lxml")

        name = bs.find('h1', 'client_name').text.split('\n')[1].strip()

        contracts = []
        contracts_code = []

        contract_id = bs.find_all('div', id=lambda x: x and x.startswith('contract_item-'))
        for j in contract_id:
            contract = j['id'].split('-')[1]
            contract_code = j['id'].split('-')[2]
            contracts.append(contract)
            contracts_code.append(contract_code)

        for i, j in zip(contracts, contracts_code):
            card_data = bs.find('div', id=f'contract_item-{i}-{j}')
            card_name_set = card_data.find('div', 'contract_item-name')
            card_name_data = card_name_set.text.strip().split('\n')
            try:
                subscription_price_rofl = float(card_name_data[0].split('/')[-1].split(')')[0])
            except:
                subscription_price_rofl = 0.0
            card_name = ' '.join(card_name_data[0].split())
            card_id_set = card_data.find('span', 'contract_item-id')
            card_code = card_id_set.text.replace('#', '').strip()

            table = card_data.find('table', 'table table-bordered table-striped table-hover')
            td_elements = table.find_all('td')
            subscription_list = []
            for k in range(0, len(td_elements), 2):
                label = td_elements[k].get_text(strip=True)
                value = td_elements[k + 1].get_text(strip=True)
                subscription_list.append((label, value))
            card_id = subscription_list[0][1]
            date_payment = subscription_list[5][1]
            date_start = subscription_list[6][1]
            date_end = subscription_list[7][1]

            try:
                subscription_price_goal = float(
                    subscription_list[9][1].split('из ')[1].split(',00')[0].strip().replace(' ', ''))

            except:
                subscription_price_goal = 0.0

            try:
                subscription_price_current = float(
                    subscription_list[9][1].split('из ')[0].split(',00')[0].strip().replace(' ', ''))

            except:
                subscription_price_current = 0.0
            subscription_price_sum = 0.0
            response_2 = s.get(
                f'https://encoreiset.fitbase.io/clients/finanse-stat-contract?type=one_contract&contract_id={i}&card_id={card_id}',
                headers=headers)
            bs2 = BeautifulSoup(response_2.text, 'lxml')
            pay_table = bs2.find_all('tr')
            for i in pay_table[1:]:
                tds = i.find_all('td')
                subscription_price_sum += float(tds[2].text) + float(tds[3].text)

            subscription_price = max(subscription_price_sum, subscription_price_current, subscription_price_goal,
                                     subscription_price_rofl)

            pattern = r'\d\d.\d\d.\d\d\d\d'
            if re.match(pattern, date_end):
                # date_end - дата окончания абонемента
                # date_end.split('.')[2] - year
                # date_end.split('.')[1] - month
                # [2] > 2025 or ([2] == 2025 and [1] >= 7) = дата окончания >= 2025-07-01
                # [2] > 2025 or ([2] == 2025 and [1] >= 12) = дата окончания >= 2025-12-01
                # [2] == 2025 and [1] >= 10 or [2] > 2025 or not date_end = дата окончания >= 2025-10-01 or null
                if int(date_end.split('.')[2]) >= 2026:
                    obj = [
                        name,  # имя
                        client_id,  # id клиента
                        # card_id,                  # название (hex) абонемента
                        card_name,  # название абонемента
                        card_code,  # код абонемента
                        date_payment,  # дата оплаты
                        date_start,  # дата активации
                        date_end,  # дата окончания
                        # contact,                  # контакты
                        subscription_price,  # полная стоимость
                        subscription_price_rofl,  # Сумма из названия
                        subscription_price_sum,  # Сумма платежей из истории
                        subscription_price_current,  # x (x из ...)
                        subscription_price_goal,  # x (... из x)
                    ]

                    data.append(obj)
                    print(obj)

    except Exception as e:
        print(f'Error in request: {e}')
    finally:
        pass


if __name__ == '__main__':

    try:
        with open('user.txt', 'r') as f:
            content = f.readlines()
        user_login = content[0].strip()
        user_password = content[1].strip()
        if user_login == '' or user_password == '':
            exit()
    except Exception as e:
        print(f'Error with open user.txt: {e}')
        exit()

    s = requests.Session()
    s.headers.update({'user-agent': custom_user_agent})

    url = 'https://encoreiset.fitbase.io'

    try:
        driver = open_driver()
        print('Драйвер успешно создан')
    except Exception as e:
        print(f'Ошибка создания драйвера: {e}')
        print(f'Тип ошибки: {type(e)}')

    cookies = get_cookie()
    last_client = add_cookie(cookies)
    first_client, last_client = 1, last_client
    # first_client, last_client = 4510, 4550
    # first_client, last_client = 2882, 2892
    # first_client, last_client = 4800, 4900
    # first_client, last_client = 44, 45
    # first_client, last_client = 145, 165

    data = []

    for i in range(first_client, int(last_client) + 1):
        request(i)

    columns = ['ФИО',
               'ID клиента',
               'Имя абонемента',
               'ID абонемента',
               'Дата оплаты',
               'Дата активации',
               'Дата окончания',
               'Стоимость абонемента (max)',
               'Сумма из названия',
               'Сумма платежей из истории',
               'x (x из ...)',
               'x (... из x)']

    if data != []:
        df = pd.DataFrame(data, columns=columns)
        while True:
            final = 0
            try:
                with pd.ExcelWriter(f'subscriptions ({first_client}-{last_client}).xlsx', engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                final = 1
            except:
                print('Ошибка записи в файл')
                time.sleep(1)
            if final == 1:
                print('Данные записаны')

                workbook = load_workbook(f'subscriptions ({first_client}-{last_client}).xlsx')
                sheet = workbook.active
                for column in sheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    sheet.column_dimensions[column_letter].width = adjusted_width

                workbook.save(f'subscriptions ({first_client}-{last_client}).xlsx')
                break
