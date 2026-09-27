import requests
import time
from concurrent.futures import ThreadPoolExecutor
import redis
import hashlib
from config import routes
import logging
from tg import send_telegram
import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("parser.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

BASE_URL = "https://saf.komissionki.ru/api/product-filter/filter"

BATCH_SIZE = 5
PAUSE = 0.5
IS_START = False

r = redis.Redis(host="redis", port=6379, decode_responses=True,)

def get_redis_key(route):
    route_hash = hashlib.md5(
        route.encode()
    ).hexdigest()

    return f"parser:records:{route_hash}"

def parse_route(route):
    url = BASE_URL + route
    try:
        response = requests.get(
            BASE_URL + route,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()

        records = data["data"]["data"]

        key = get_redis_key(route)

        old_ids = set(r.lrange(key, 0, -1))

        new_records = []

        for record in records:
            record_id = str(record["id"])

            if record_id not in old_ids:
                new_records.append(record)

        pipe = r.pipeline()
        pipe.delete(key)

        if records:
            pipe.rpush(key, *[str(record["id"]) for record in records])

        pipe.execute()

        return route, new_records
    except requests.Timeout:
        logger.error(
            f"Timeout: {url}"
        )

    except requests.HTTPError as e:
        logger.error(
            f"HTTP ошибка {e.response.status_code}: {url}"
        )

    except requests.RequestException as e:
        logger.error(
            f"Ошибка запроса: {url}. {e}"
        )

    except ValueError:
        logger.error(
            f"Ошибка JSON: {url}"
        )

    except Exception:
        logger.exception(
            f"Неизвестная ошибка: {url}"
        )

    return route, []

def parse_phones():
    global IS_START
    with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
        for i in range(0, len(routes), BATCH_SIZE):
            batch = routes[i:i + BATCH_SIZE]

            results = executor.map(parse_route, batch)

            for route, new_records in results:
                if IS_START:
                    for record in new_records:
                        date = datetime.datetime.fromisoformat(record['updatedAt'].replace('Z', '+00:00'))
                        txt = f"НОВАЯ: {record['title']} ({record['price']} р.). Дата: {date}. Ссылка: https://komissionki.ru/catalog/telefony/sotovye-telefony/{record['code']}/"
                        #print(txt)
                        try:
                            send_telegram(txt)
                        except Exception:
                            logger.exception(f"Неизвестная ошибка: НОВАЯ: {record['id']} " f"{record['title']}")

            if i + BATCH_SIZE < len(routes):
                time.sleep(PAUSE)

    IS_START = True

while True:
    parse_phones()
    time.sleep(20)