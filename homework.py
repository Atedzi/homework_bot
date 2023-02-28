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
    'approved': '������ ���������: �������� �� �����������. ���!',
    'reviewing': '������ ����� �� �������� ���������.',
    'rejected': '������ ���������: � �������� ���� ���������.'
}


def check_tokens():
    """�������� ������� ������������ ����������."""
    logging.info('�������� ������� ���� �������')
    if all((PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN)):
        return bool


def send_message(bot, message):
    """���������� ��������� � Telegram ���."""
    try:
        logging.info('�������� �������')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as error:
        logging.error('TelegramError:', error)
        return('TelegramError:', error)
    except Exception:
        logging.error('�������� ������ ��������')
        return('�������� ������ ��������')
    else:
        logging.debug(f'��������� ���������� {message}')


def get_api_answer(timestamp):
    """������ ������ � API."""
    TimeStamp = timestamp or int(time.time())
    params_request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': TimeStamp},
    }
    message = ('������: {url}, {headers}, {params}.'
               ).format(**params_request)
    logging.info(message)
    try:
        response = requests.get(**params_request)
        if response.status_code != HTTPStatus.OK:
            raise WrongResponseCode(
                f'��� ������. '
                f'��� ������: {response.status_code}. '
                f'��� �� ���: {response.reason}. '
                f'�����: {response.text}.'
            )
        return response.json()
    except Exception as error:
        message = ('��� ������. ������: {url}, {headers}, {params}.'
                   ).format(**params_request)
        raise WrongResponseCode(message, error)


def check_response(response):
    """��������� ����� API �� ������������."""
    logging.debug('������ ��������')
    if not isinstance(response, dict):
        raise TypeError('����� API �� �������� ��������')
    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError('����������� ����')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('����� API �� �������� ������')
    return homeworks


def parse_status(homework):
    """������ ��������� ������. ��������� � ����������� � ��."""
    if 'homework_name' not in homework:
        raise KeyError('����������� ���� "homework_name" � ������')
    if 'status' not in homework:
        raise KeyError('����������� ���� "status" � ������')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    try:
        verdict = HOMEWORK_VERDICTS[homework_status]
    except KeyError as errkey:
        logger.error('Undocumented status of homework.', errkey)
        return ('Undocumented status of homework.', errkey)
    return f'��������� ������ �������� ������ "{homework_name}". {verdict}'


def main():
    """�������� ������ ������ ����."""
    if not check_tokens():
        logging.critical('����������� �����. ��� ����������!')
        sys.exit('����������� ���� ��� ��������� �������. ��� ����������!')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    send_message(bot, '�����!')
    logging.info('�����!')
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
                message = '������ �� �� ��������'
            if message != error_msg:
                send_message(bot, message)
                error_msg = message
            else:
                logging.info(message)
        except Exception as error:
            message = f'� ������ ���� ���������� ����: {error}'
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
