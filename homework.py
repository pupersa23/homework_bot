import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import json
from dotenv import load_dotenv
from telegram import Bot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(message)s',
    handlers=[logging.FileHandler('log.txt'),
              logging.StreamHandler(sys.stdout)])

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщение в чатбот."""
    return bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Запрос данных с сервера практикума."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException as e:
        logging.error(f'Сервер Яндекс.Практикум вернул ошибку: {e}')
    try:
        return response.json()
    except json.JSONDecodeError:
        logging.error('Сервер вернул невалидный json')


def check_response(response):
    """Проверка корекктности переданных данных сервером."""
    if type(response) is not dict:
        raise TypeError('Response не формата  dict')
    elif len(response) == 0:
        raise Exception('Response пустой')
    elif 'homeworks' not in response.keys():
        raise Exception('Нет ключа в response')
    elif type(response['homeworks']) is not list:
        raise Exception('Тип homeworks не list')
    else:
        return response['homeworks']


def parse_status(homework):
    """Определние типа готовности домашней работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']

    if ((homework_status is None) or (
            homework_status == '')) or ((
            homework_status != 'approved') and (
            homework_status != 'rejected')):
        raise Exception(f'Статус работы некорректен: {homework_status}')

    verdict = ''

    if homework_status == 'approved':
        verdict = HOMEWORK_STATUSES['approved']
    elif homework_status == 'reviewing':
        verdict = HOMEWORK_STATUSES['reviewing']
    elif homework_status == 'rejected':
        verdict = HOMEWORK_STATUSES['rejected']
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка на наличие токенов."""
    if not PRACTICUM_TOKEN:
        return False
    elif not TELEGRAM_TOKEN:
        return False
    elif not TELEGRAM_CHAT_ID:
        return False
    else:
        return True


def main():
    """Основная работа бота."""
    logging.info('Бот запущен')
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = 30

    while True:
        try:
            if check_tokens() is True:
                response = get_api_answer(timestamp)
                check_response(response)
                parse_status(response['homeworks'][0])
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            current_timestamp = int(time.time())
            response = get_api_answer(current_timestamp)
            if len(response['homeworks']) > 0:
                homework = response['homeworks'][0]
                send_message(bot, parse_status(homework))
                logging.info('Сообщение отправлено')
                time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
