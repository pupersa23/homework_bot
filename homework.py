import logging
import os
import sys
import time

import requests
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
    return bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        raise 'Неверный статус код'
    return response.json()


def check_response(response):
    if type(response) is not dict:
        raise 'Response не формата  dict'
    elif len(response) == 0:
        raise 'Response пустой'
    elif 'homeworks' not in response.keys():
        raise 'Нет ключа в response'
    elif type(response['homeworks']) is not list:
        raise 'Тип homeworks не list'
    else:
        return response['homeworks']


def parse_status(homework):
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
    if not PRACTICUM_TOKEN:
        return False
    elif not TELEGRAM_TOKEN:
        return False
    elif not TELEGRAM_CHAT_ID:
        return False
    else:
        return True


def main():

    logging.debug('Бот запущен')
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            tokens = check_tokens()
            if tokens is False:
                raise Exception('Отсутствует token')
            response = get_api_answer(current_timestamp)
            check = check_response(response)
            if check != response['homeworks']:
                raise Exception('Ошибка ответа сервера')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            response = get_api_answer(current_timestamp)
            if len(response['homeworks']) > 0:
                homework = response['homeworks'][0]
                send_message(parse_status(homework))
                logging.info('Сообщение отправлено')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
