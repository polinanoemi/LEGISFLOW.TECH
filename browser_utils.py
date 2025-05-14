import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import selenium
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import sqlite3
from sqlite3 import Cursor
import requests
from urllib.parse import urlparse
import urllib.request
from adds import *

import time
import random
import urllib.request
from selenium.webdriver import Chrome, ChromeOptions
import pathlib
import pymupdf
from striprtf.striprtf import rtf_to_text
import os
import shutil
import glob
from openai import OpenAI
import pymorphy2
from sqlite3 import IntegrityError

BOT_TOKEN = '7964962560:AAGF2LldCw0dZfqcqY0IAokhEbgvN9kIfkM'
LINK = 'http://45.143.93.208/home'
ADMIN_ID = 913556935



class NoDocument(Exception):
    pass


class APIError(Exception):
    pass


class UnknownWord(Exception):
    pass


def date_formatter():
    today = datetime.datetime.today().strftime('%d.%m.%Y')
    return today


NEURO_TOKEN = 'sk-4d0edbd9e5c74734abce9da5cac5d20a'
NEURO_LINK = 'https://api.deepseek.com'
# REGULATION_LINK = 'https://regulation.gov.ru/projects'
REGULATION_LINK = 'https://regulation.gov.ru/projects#StartDate=4.3.2025'

REGULATION_TIMEOUT = 240

morph = pymorphy2.MorphAnalyzer()


def projects_by_list(list_id: int, cursor):
    words = cursor.execute(SELECT_FROM_LIST, (list_id,)).fetchall()
    words = [word[0] for word in words]
    res = projects_by_words(words)
    return res


def delete_word(word: str, cursor) -> None:
    """accepts only already created word in first form"""
    word_id = cursor.execute(SELECT_WORD_BY_TEXT, (word,)).fetchone()  # FIX unfinished


def advanced_words_creator(words: list[str], cursor):
    res = []
    for word in words:
        parse = morph.parse(word)[0]
        try:
            main_form = parse.inflect({'nomn'}).text
        except AttributeError:
            main_form = parse.normal_form

        word_id = cursor.execute(SELECT_WORD_BY_TEXT, (main_form,)).fetchone()
        if word_id:
            res.append(word_id[0])
            continue
        else:
            res_texts = set()
            try:
                for form in parse.inflect({'nomn'}).lexeme:
                    res_texts.add(form.word)
                cursor.execute(CREATE_WORD, (main_form,))
                word_id = cursor.execute(SELECT_WORD_BY_TEXT, (main_form,)).fetchone()[0]
                res.append(word_id)
            except AttributeError:
                telegram_send_to_admin('bad word, skipping: ' + word)
                continue
            for text in res_texts:
                projects_ids = [item[0] for item in cursor.execute(SEARCH_WORD, (text,)).fetchall()]
                for project_id in projects_ids:
                    try:
                        cursor.execute(CREATE_CONNECTION, (project_id, word_id))
                    except sqlite3.IntegrityError:
                        continue

    return res


def advanced_words_re_searcher(words: list[str], cursor):
    """:arg words: only already created words"""
    res = []
    for word in words:
        parse = morph.parse(word)[0]
        try:
            main_form = parse.inflect({'nomn'}).text
        except AttributeError:
            main_form = parse.normal_form

        word_id = cursor.execute(SELECT_WORD_BY_TEXT, (main_form,)).fetchone()[0]
        res.append(word_id)
        res_texts = set()
        for form in parse.inflect({'nomn'}).lexeme:
            res_texts.add(form.word)

        for text in res_texts:
            projects_ids = [item[0] for item in cursor.execute(SEARCH_WORD, (text,)).fetchall()]
            for project_id in projects_ids:
                try:
                    cursor.execute(CREATE_CONNECTION, (project_id, word_id))
                except sqlite3.IntegrityError:
                    continue

    return res


def advanced_project_text_search(project_id: int, cursor):
    project_text = cursor.execute(PROJECT_TEXT_BY_ID, (project_id,)).fetchone()[0]
    words = cursor.execute(SELECT_ALL_WORDS).fetchall()
    for word, word_id in words:
        parse = morph.parse(word)[0]

        res_texts = set()
        for form in parse.inflect({'nomn'}).lexeme:
            res_texts.add(form.word)

        for word_form in res_texts:
            if f' {word_form} ' in f" {project_text} ":
                cursor.execute(CREATE_CONNECTION, (project_id, word_id))
                break


def telegram_bot_sendtext(project_id, user_id, cursor):
    text = f'Здравствуйте, на сайте новый законопроект, прошедший ваши фильтры: <a href="{LINK}">{project_id}</a>'
    tg_id = cursor.execute(GET_TG_ID, (user_id,)).fetchone()[0]
    send_text = 'https://api.telegram.org/bot' + BOT_TOKEN + '/sendMessage?chat_id=' + str(
        tg_id) + '&parse_mode=HTML&text=' + text
    response = requests.get(send_text)
    return response.json()


def telegram_send_to_admin(message: str):
    send_text = 'https://api.telegram.org/bot' + BOT_TOKEN + '/sendMessage?chat_id=' + str(
        ADMIN_ID) + '&parse_mode=HTML&text=' + message
    response = requests.get(send_text)
    return response.json()


def word_in_project_check(project_id: int, word_id: int, cursor):
    project_text = cursor.execute(PROJECT_TEXT_BY_ID, (project_id,)).fetchone()[0]
    word = cursor.execute(GET_WORD_BY_ID, (word_id,)).fetchone()[0]
    parse = morph.parse(word)[0]

    res_texts = set()
    for form in parse.inflect({'nomn'}).lexeme:
        res_texts.add(form.word)
    for word_form in res_texts:
        if f' {word_form} ' in f" {project_text} ":
            break


def projects_by_words(words: list[str]) -> dict[list[int]]:
    """:arg words: accept only already created words
    :returns: dict with projects ids as keys to words"""
    result = {}
    for word in words:
        tmp = cursor.execute(SELECT_WORD_BY_TEXT, (word,)).fetchone()
        if tmp:
            word_id = tmp[0]
            connections = cursor.execute(SELECT_CONNECTIONS_BY_WORD, (word_id,)).fetchall()
            for project_id in connections:
                project_id = project_id[0]
                if project_id in result.keys():
                    result[project_id].append(word)
                else:
                    result[project_id] = [word]
        else:
            raise UnknownWord
    return result


def regulation_open_project_info(driver: webdriver, link: str, ):
    driver.get(link)
    try:
        element = WebDriverWait(driver, REGULATION_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, "//div[@data-stage='20']"))
        )
    except NoSuchElementException:
        telegram_send_to_admin('timeout, exiting REGULATION PARSE')
        driver.quit()
        raise TimeoutError
    time.sleep(1)
    try:
        open_info = element.find_element(By.CLASS_NAME, 'btns-group')
        open_info = WebDriverWait(open_info, REGULATION_TIMEOUT).until(
            EC.element_to_be_clickable((By.TAG_NAME, 'a'))
        )
    except NoSuchElementException:
        try:
            open_info = driver.find_element(By.XPATH, "//a[contains(text(), 'Информация по этапу')]")
            open_info = WebDriverWait(driver, REGULATION_TIMEOUT).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Информация по этапу')]"))
            )
        except NoSuchElementException:
            telegram_send_to_admin('error in opening project info regulation')
            return 1
    open_info.click()
    time.sleep(0.5)


def work_with_regulation_link(driver: webdriver, link: str, cursor: Cursor) -> (str, int):
    if regulation_open_project_info(driver, link) is not None:
        return '', -1, ''

    preview_block = driver.find_element(By.CLASS_NAME, 'dl-horizontal')
    rows = preview_block.find_elements(By.TAG_NAME, 'dd')
    file_opener = None
    project_name = driver.find_element(By.CLASS_NAME, 'public_view_npa_title_text')
    project_name = project_name.text
    for row in rows:
        try:
            file_opener = row.find_element(By.TAG_NAME, 'a')
            break
        except NoSuchElementException:
            continue

    if file_opener is None:
        telegram_send_to_admin("error in file search regulation")
        raise NoDocument

    try:
        file_id = file_opener.get_attribute('onclick').split("showDoc('")[-1][:-2]
        file_link = f'https://regulation.gov.ru/Files/GetFile?fileid={file_id}'
    except AttributeError:
        file_link = file_opener.get_attribute('href')
    driver.get(file_link)
    time.sleep(3)  # wait for the file to download
    project_id = int(link.split('=')[-1])
    file_path = max([os.path.join(DIR_PATH, d) for d in os.listdir(DIR_PATH)], key=os.path.getmtime)
    return file_path, project_id, project_name


def work_with_sozd_duma_link(driver: webdriver, link: str):
    driver.get(link)
    project_name = driver.find_element(By.ID, 'oz_name').text
    table = driver.find_element(By.CLASS_NAME, 'table-hover')
    try:
        file_link = table.find_element(By.TAG_NAME, 'a').get_attribute('href')
    except NoSuchElementException:
        return '', -1

    driver.get(file_link)
    time.sleep(3)

    file_name = max([os.path.join(DIR_PATH, d) for d in os.listdir(DIR_PATH)], key=os.path.getmtime)
    if '/' in file_name:
        file_name = file_name.split('/')[-1]
    else:
        file_name = file_name.split('\\')[-1]
    project_id = link.split('/bill/')[-1].replace('-', '')

    return file_name, project_id, project_name


def extract_text(file_path: str) -> str:
    """:returns: extracted lowered text"""
    if '.rtf' in file_path:
        with open(file_path) as f:
            content = f.read()
            text = rtf_to_text(content)
    else:
        with pymupdf.open(file_path) as doc:
            text = chr(12).join([page.get_text() for page in doc.pages()])
    text = text.replace('\t', ' ').replace('\n', ' ')
    while '  ' in text:
        text = text.replace('  ', ' ')
    return text.lower()


def neuro_short_text(full_text: str) -> str:
    """:return: shortened_text"""
    client = OpenAI(api_key=NEURO_TOKEN, base_url=NEURO_LINK)
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user",
             "content": "Выдели ключевые моменты этого законопроекта, сократи текст до 100 слов или менее. Не используй форматирование текста, такое как ** и т.п., также не отправляй мне никаких пояснений, вроде 'Краткое содержание законопроекта (100 слов):', только сокращенный текст, пользователю известно, что это законопроект, так что не используй конструкции 'этот законопроект' и т.п. Если в тексте нет законопроекта верни строку 'законопроект отсутствует'" + full_text}
        ],
        stream=False
    )
    try:
        resulted_text = response.choices[0].message.content
        if resulted_text == 'законопроект отсутствует':
            return ''
        return resulted_text
    except KeyError:
        try:
            event = response.error.message
            telegram_send_to_admin("error in neural network request," + str(event))
        except KeyError:
            telegram_send_to_admin("unexpected error response")
        raise APIError
    except Exception as e:
        telegram_send_to_admin('unexpected behavior,' + str(e))


def parse_regulation(driver: webdriver, cursor: Cursor, stop_after=0):
    driver.get(REGULATION_LINK)
    links = LinksList(cursor, REGULATION_FLAG, stop_after)
    flag = True
    while flag:
        table = WebDriverWait(driver, REGULATION_TIMEOUT).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'k-listview')))
        time.sleep(0.5)

        for project in table.find_elements(By.CLASS_NAME, 'title'):
            link = project.get_attribute('href')
            if links.append(link) is not None:
                flag = False
                break

        pager_info = driver.find_element(By.CLASS_NAME, 'k-pager-info').text.split(' ')
        end, amount = int(pager_info[2]), int(pager_info[4])  # запись вида "1 - 20 из 33 записей"
        if end == amount:
            break

        tmp = driver.find_elements(By.XPATH, "//*[contains(text(), 'Следующая')]")
        tmp[0].click()
        time.sleep(1)

    counter = 0
    for link in links:
        file_path, project_id, project_name = work_with_regulation_link(driver, link, cursor)
        if project_id == -1:
            telegram_send_to_admin(f'skipping link {link}, no text yet')

            continue
        text = extract_text(file_path)
        if '/' in file_path:
            file_name = file_path.split('/')[-1]
        else:
            file_name = file_path.split('\\')[-1]
        shortened_text = neuro_short_text(text)
        if not shortened_text:
            telegram_send_to_admin(f"Skipping {link}, {file_name}, probably bad file, no text")

            continue
        date = date_formatter()

        try:
            cursor.execute(CREATE_PROJECT,
                           (link, file_name, shortened_text, text, project_id, REGULATION_FLAG, project_name, date))
        except IntegrityError:
            telegram_send_to_admin('Somehow, already seen project' + str(project_id))
            continue
        advanced_project_text_search(project_id, cursor)
        notify(project_id, cursor)
        counter += 1
        telegram_send_to_admin(f'{counter} done')


def parse_sozd_duma(driver: webdriver, cursor: Cursor, stop_after=0):
    counter = 1
    links = LinksList(cursor, SOZD_DUMA_FLAG, stop_after)
    flag = True
    while flag:
        driver.get(f'https://sozd.duma.gov.ru/search?q=&page={counter}&count_items=300#data_source_tab_b')

        for elem in driver.find_elements(By.CLASS_NAME, 'click_open'):
            law_id: str = elem.find_element(By.TAG_NAME, 'strong').text
            link = 'https://sozd.duma.gov.ru/bill/' + law_id
            if links.append(link) is not None:
                flag = False
                break

        driver.get(f'https://sozd.duma.gov.ru/search?q=&page={counter}&count_items=300#data_source_tab_b')
        counter += 1
        next = driver.find_element(By.CLASS_NAME, 'navigation_ten').find_elements(By.TAG_NAME, "li")[-1]
        if next.get_attribute('class') == 'disabled':
            break

    for link in links:
        file_name, project_id, project_name = work_with_sozd_duma_link(driver, link)
        text = extract_text(file_name)
        shortened_text = neuro_short_text(text)
        if not shortened_text:

            telegram_send_to_admin(f"Skipping {link}, {file_name}, probably bad file, no text")
        date = date_formatter()
        try:
            cursor.execute(CREATE_PROJECT,
                           (link, file_name, shortened_text, text, project_id, SOZD_DUMA_FLAG, project_name, date))
        except IntegrityError:
            telegram_send_to_admin('Somehow, already seen project' + str(project_id))
        advanced_project_text_search(project_id, cursor)
        notify(project_id, cursor)
    telegram_send_to_admin(f"sozd duma finished, {len(links)} links len")


def lower_texts(cursor):
    """Run only after mistaken inputs"""
    for project_id, text in cursor.execute(SELECT_FOR_LOWERING).fetchall():
        cursor.execute(UPDATE_TEXT, (text.lower(), project_id))


def notify(project_id: int, cursor):
    user_ids = [item[0] for item in cursor.execute(GET_PROJECT_VIEWERS, (project_id,)).fetchall()]
    for user_id in user_ids:
        cursor.execute(CREATE_NOTIFICATION, (user_id, project_id))
        tg_id = cursor.execute(GET_TG_ID, (user_id,)).fetchone()[0]
        if tg_id is not None:
            project_type = cursor.execute(GET_PROJECT_TYPE, (project_id,)).fetchone()[0]
            project_id = format_id(project_id, project_type)
            telegram_bot_sendtext(project_id, user_id, cursor)


if __name__ == "__main__":
    DIR_PATH = pathlib.Path('files').resolve()

    prefs = {
        "download.default_directory": str(DIR_PATH),
        "download.directory_upgrade": True,
        "download.prompt_for_download": False
    }

    chromeOptions = webdriver.ChromeOptions()
    chromeOptions.add_experimental_option("prefs", prefs)
    chromeOptions.page_load_strategy = 'eager'
    chromeOptions.add_argument("--headless=new")
    chromeOptions.binary_location = "chrome-linux64/chrome"

    CHROME_PATH = pathlib.Path('chromedriver-linux64/chromedriver').resolve()
    service = webdriver.ChromeService(executable_path=str(CHROME_PATH))

    driver = webdriver.Chrome(options=chromeOptions, service=service)
    conn = sqlite3.connect('main.db', check_same_thread=False)
    conn.isolation_level = None
    cursor = conn.cursor()
    parse_regulation(driver, cursor, 10)
    parse_sozd_duma(driver, cursor, 10)
