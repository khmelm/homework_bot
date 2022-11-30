import logging
import os
import requests
import time
import sys

from dotenv import load_dotenv

from http import HTTPStatus

import telegram

load_dotenv()


PRACTICUM_TOKEN = os.getenv('YATOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)


def check_tokens() -> bool:
    """Проверяем наличие токенов."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправляет сообщение."""
    logging.info('Начинаем отправку сообщения')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception:
        logging.error('Ошибка в отправке сообщения')
    else:
        logging.debug('Сообщение успешно отправлено')


def get_api_answer(timestamp):
    """Делаем запрос на сервер."""
    logging.info('Начинаем формирование запрос к API')
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            response.raise_for_status()
        logging.info('Ответ на запрос к API: OK')
        return response.json()
    except requests.exceptions.RequestException:
        message = f'Ошибка при запросе к API:{response.status_code}'
        raise requests.exceptions.RequestException(message)


def check_response(response):
    """Проверяем ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('API возвращает не словарь.')
    if 'homeworks' not in response:
        raise KeyError('В запросе нет словаря homeworks')
    if 'current_date' not in response:
            raise KeyError('В запросе нет текущей даты')
    else:
        homeworks = response['homeworks']
        if not isinstance(homeworks, list):
            raise TypeError('Словарь homeworks возвращает не лист.')
        return response.get('homeworks')


def parse_status(homework):
    """Проверяем статус домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if 'homework_name' not in homework:
        raise KeyError('В homeworks отсутствует имя домашки')
    if 'status' not in homework:
        raise KeyError('В homeworks нет ключа status.')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(
                'В HOMEWORK_VERDICTS нет ключа homework_status.')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return ('Изменился статус проверки работы '
            f'"{homework_name}". {verdict}')


def main():
    """Главная функция."""
    logging.info('Бот запущен')
    if not check_tokens():
        message = 'Отсутвует один или несколько токенов'
        logging.critical(message)
        sys.exit(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    previous_message = ''
    logging.info('Токены найдены')
    while True:
        try:
            response_result = get_api_answer(timestamp)
            homeworks = check_response(response_result)
            logging.info("Список домашних работ получен")
            if homeworks:
                message = parse_status(homeworks[0])
                timestamp = response_result['current_date']
                if message != previous_message:
                    send_message(bot, message)
                    previous_message = message
            else:
                logging.info("Новые задания не обнаружены")
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
