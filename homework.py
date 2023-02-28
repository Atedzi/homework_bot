# coding=windows-1251
import logging
import os
import sys
import requests
import telegram
import time

from dotenv import load_dotenv
from exceptions import WrongResponseCode
from http import HTTPStatus

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка наличия обязательных переменных."""
    logging.info('Проверка наличия всех токенов')
    if all((PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN)):
        return bool


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.info('Отправка статуса')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as error:
        logging.error('TelegramError:', error)
        return('TelegramError:', error)
    except Exception:
        logging.error('Возникла другая проблема')
        return('Возникла другая проблема')
    else:
        logging.debug(f'Сообщение отправлено {message}')


def get_api_answer(timestamp):
    """Делаем запрос к API."""
    TimeStamp = timestamp or int(time.time())
    params_request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': TimeStamp},
    }
    message = ('Запрос: {url}, {headers}, {params}.'
               ).format(**params_request)
    logging.info(message)
    try:
        response = requests.get(**params_request)
        if response.status_code != HTTPStatus.OK:
            raise WrongResponseCode(
                f'Нет ответа. '
                f'Код ответа: {response.status_code}. '
                f'Что не так: {response.reason}. '
                f'Текст: {response.text}.'
            )
        return response.json()
    except Exception as error:
        message = ('Нет ответа. Запрос: {url}, {headers}, {params}.'
                   ).format(**params_request)
        raise WrongResponseCode(message, error)


def check_response(response):
    """Проверяем ответ API на корректность."""
    logging.debug('Начало проверки')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем')
    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError('Отсутствует ключ')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Ответ API не является листом')
    return homeworks


def parse_status(homework):
    """Статус последней работы. Сообщение с информацией о нём."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ "status" в ответе')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    try:
        verdict = HOMEWORK_VERDICTS[homework_status]
    except KeyError as errkey:
        logger.error('Undocumented status of homework.', errkey)
        return ('Undocumented status of homework.', errkey)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует токен. Бот остановлен!')
        sys.exit('Отсутствует один или несколько токенов. Бот остановлен!')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    send_message(bot, 'Старт!')
    logging.info('Старт!')
    error_msg = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get(
                'current_date', int(time.time())
            )
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = 'Статус дз не обнавлен'
            if message != error_msg:
                send_message(bot, message)
                error_msg = message
            else:
                logging.info(message)
        except Exception as error:
            message = f'В работе бота произошлел сбой: {error}'
            logging.error(message, exc_info=True)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename='main.log',
        format='%(asctime)s, %(levelname)s, %(name)s, %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(stream=sys.stdout)
    logger.addHandler(handler)
    main()
