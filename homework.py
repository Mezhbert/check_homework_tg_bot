import os
import sys
import time
import logging
import requests
from telegram import Bot
from dotenv import load_dotenv
from constants import TOKEN_ERR, MISSING_KEY, WRONG_DATA_STRUCTRE

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s,%(levelname)s %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')
stream_handler.setFormatter(formatter)

logging.getLogger().addHandler(stream_handler)

load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщения по адресу TELEGRAM_CHAT_ID."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug("Сообщение удачно отправлено.")
    except Exception as e:
        logging.error(f"Сбой при отправке сообщения: {e}")


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params={'from_date': timestamp})
        if response.status_code != 200:
            raise Exception(f"Ошибка доступа эндпоинта: статус "
                            f"{response.status_code}")

        return response.json()
    except requests.RequestException as e:
        err_message = 'Сбой при запросе к эндпоинту:'
        logging.error(f"{err_message} {e}")
        raise Exception(f"{err_message} {e}")


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error(WRONG_DATA_STRUCTRE)
        raise TypeError(WRONG_DATA_STRUCTRE)
    if not ('homeworks' in response):
        logging.error(MISSING_KEY)
        raise KeyError(MISSING_KEY)
    if not isinstance(response.get('homeworks'), list):
        logging.error(WRONG_DATA_STRUCTRE)
        raise TypeError(WRONG_DATA_STRUCTRE)

    return response['homeworks']


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')

    if not homework_name:
        raise KeyError("Отсутствует ключ 'homework_name'")

    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f"Неожиданный статус домашней работы: {status}")

    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.debug("Запуск основной логики бота.")

    if not check_tokens():
        logging.critical(TOKEN_ERR)
        sys.exit(TOKEN_ERR)

    logging.debug("Проверка переменных окружения - успешно.")

    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                message = parse_status(homework)
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
