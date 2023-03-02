import logging
import os
import requests
import sys
import telegram
import time

from dotenv import load_dotenv
from exceptions import WrongResponseCode
from http import HTTPStatus
from requests import RequestException

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
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as error:
        logging.error('TelegramError:', error)
    else:
        logging.debug(f'Отправка сообщения {message}')


def get_api_answer(timestamp):
    """Делаем запрос к API."""
    params = {'from_date': timestamp}
    params_request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': params},
    }
    message = ('Запрос: {url}, {headers}, {params}.'
               ).format(**params_request)
    logging.info(message)
    try:
        response = requests.get(**params_request)
        if response.status_code != HTTPStatus.OK:
            raise WrongResponseCode(
                f'Ответ не получен. '
                f'Код ответа: {response.status_code}. '
                f'Причина: {response.reason}. '
                f'Текст: {response.text}.'
            )
        return response.json()
    except RequestException as error:
        message = ('Запрос: {url}, {headers}, {params}.'
                   ).format(**params_request)
        raise WrongResponseCode(message, error)


def check_response(response):
    """Проверить валидность ответа."""
    logging.debug('Проверка ответа API на корректность')
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является dict')
    if 'homeworks' not in response:
        raise KeyError('Нет ключа homeworks в ответе API')
    if 'current_date' not in response:
        raise KeyError('Нет ключа current_date в ответе API')
    current_date = response['current_date']
    if not isinstance(current_date, int):
        raise TypeError('current_date не является целым числом')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('homeworks не является list')
    return homeworks


def parse_status(homework):
    """Извлекает информацию о домашней работе."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ "status" в ответе API')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(
            f'{homework_status} нет в словаре HOMEWORK_VERDICTS'
        )
    verdict = HOMEWORK_VERDICTS[homework_status]
    homework_name = homework.get('homework_name')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствует токен. Бот остановлен!')
        sys.exit('Отсутствует токен. Бот остановлен!')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    send_message(bot, 'Старт!')
    logging.info('Старт!')
    error_msg = ''

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                message = 'Нет новых статусов'
            timestamp = response.get(
                'current_date', int(time.time())
            )
            if message != error_msg:
                send_message(bot, message)
                error_msg = message
            else:
                logging.info(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename='main.log',
        format='%(asctime)s, %(levelname)s, %(name)s, %(message)s')
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler(stream=sys.stdout)
    logger.addHandler(handler)
    main()
