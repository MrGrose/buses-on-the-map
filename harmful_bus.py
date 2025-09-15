import json
import logging
import random

import trio
from trio_websocket import ConnectionClosed, HandshakeError, open_websocket_url

logger = logging.getLogger("bad_bus")


bad_buses = [
    "",
    "not a json",
    {},
    {"buses": []},
    {"buses": {}},
    {"msgType": 123, "buses": {"south_lat": 0, "north_lat": 0, "west_lng": 0, "east_lng": 0}},
    {"msgType": "Buses"},
    {"msgType": "Buses", "buses": [{"busId": "112-2", "lat": 55.662009028248, "lng": 37.773152386955, "route": 1}]},
    {"msgType": "Buses", "buses": [{"busId": 112-2, "lat": 55.662009028248, "lng": 37.773152386955, "route": "112"}]},
    {"msgType": "wrongType", "wrongType": [{"busId": "796-0", "south_lat": 0, "north_lat": 0, "west_lng": 0, "east_lng": 0}]},
]


async def main():
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

    try:
        async with open_websocket_url('ws://127.0.0.1:8080') as ws:
            while True:
                bad_msg = random.choice(bad_buses)
                logger.info(f"Отправлено: {bad_msg}")
                await ws.send_message(json.dumps(bad_msg))

                message = await ws.get_message()
                try:
                    data = json.loads(message)
                    if "errors" in data:
                        logger.error(f"Ошибка от сервера: {data['errors']}")
                    else:
                        logger.info(f"Пришло от сервера: {data}")
                except json.JSONDecodeError:
                    logger.error(f"Невалидный ответ от сервера: {message}")

                await trio.sleep(1)

    except* KeyboardInterrupt:
        logger.info("Программа остановлена")

    except* (ConnectionClosed, OSError, HandshakeError):
        await trio.sleep(1)

trio.run(main)
