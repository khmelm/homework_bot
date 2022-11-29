import logging
import os
import requests
import time

from dotenv import load_dotenv

from http import HTTPStatus

import telegram

from telegram import Bot

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
    """Проверяем наличие токенов"""
    tokens = {
        'practicum_token': PRACTICUM_TOKEN,
        'telegram_token': TELEGRAM_TOKEN,
        'telegram_chat_id': TELEGRAM_CHAT_ID,
    }
    for key, value in tokens.items():
        if value is None:
            logging.critical(f'{key} отсутствует')
            return False
    logging.info('Токены найдены')
    return True

def send_message(bot, message):
    """Отправляет сообщение"""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception:
        logging.error('Ошибка в отправке сообщения')
    else:
        logging.debug('Сообщение успешно отправлено')
    pass

def get_api_answer(timestamp):
    """Делаем запрос на сервер"""
    params = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            response.raise_for_status()
        logging.info('Ответ на запрос к API: OK')
        return response.json()
    except requests.exceptions.RequestException:
        message = f'Ошибка при запросе к API:{response.status_code}'
        logging.error(message)
        raise requests.exceptions.RequestException(message)

def check_response(response):
    """Проверяем ответ API на соответствие документации."""
    if isinstance(response, dict):
        if 'homeworks' in response:
            if isinstance(response['homeworks'], list):
                return response.get('homeworks')
            raise TypeError('Словарь homeworks возвращает не лист.')
        raise KeyError('В запросе нет словаря homeworks')
    raise TypeError('API возвращает не словарь.')

def parse_status(homework):
    """Проверяем статус домашней работы."""
    if isinstance(homework, dict):
        if 'status' in homework:
            if 'homework_name' in homework:
                if isinstance(homework.get('status'), str):
                    homework_name = homework.get('homework_name')
                    homework_status = homework.get('status')
                    if homework_status in HOMEWORK_VERDICTS:
                        verdict = HOMEWORK_VERDICTS.get(homework_status)
                        return ('Изменился статус проверки работы 'f'"{homework_name}". {verdict}')
                    else:
                        raise Exception("Неизвестный статус работы.")
            raise KeyError('В homeworks отсутствует имя домашки')
        raise KeyError('В homeworks нет ключа status.')
    raise TypeError('Лист с домашней работой возвращает не словарь.')

def main():
    """Главная функция."""
    logging.info('Бот запущен')
    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        timestamp = int(time.time())
        while True:
            try:
                """Запрос к API."""
                response_result = get_api_answer(timestamp)
                """Проверка ответа."""
                homeworks = check_response(response_result)
                logging.info("Список домашних работ получен")
                """Если есть обновления, то отправить сообщение в Telegram."""
                if len(homeworks) > 0:
                    send_message(bot, parse_status(homeworks[0]))
                    """Дата последнего обновления."""
                    timestamp = response_result['current_date']
                else:
                    logging.info("Новые задания не обнаружены")
                time.sleep(RETRY_PERIOD)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                time.sleep(RETRY_PERIOD)
                

if __name__ == '__main__':
    main()
