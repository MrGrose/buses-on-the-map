import json
import logging
from functools import partial, wraps
from itertools import islice
from random import choice, randint

import trio
from trio_websocket import ConnectionClosed, HandshakeError, open_websocket_url

from utils import bus_parser, generate_bus_id, load_routes

logger = logging.getLogger("fake_bus")


async def run_bus(route, bus_id, send_channel, refresh_timeout):

    coordinates = route["coordinates"]
    index = randint(0, len(coordinates) - 1)
    while True:
        try:
            coor = coordinates[index]
            bus_route = {
                "msgType": "Buses",
                "buses": [{"busId": bus_id,"lat": coor[0],"lng": coor[1], "route": route["name"]}]
            }

            await send_channel.send(json.dumps(bus_route, ensure_ascii=False))
            await trio.sleep(refresh_timeout)
            index = (index + 1) % len(coordinates)

        except ConnectionClosed:
            logger.error(f"Соединение закрыто {bus_id}")
            break


def relaunch_on_disconnect(async_function):
    @wraps(async_function)
    async def wrapper(*args, **kwargs):
        while True:
            try:
                await async_function(*args, **kwargs)
            except* (ConnectionClosed, OSError, HandshakeError):
                logger.info("Ошибка соединения, переподключаемся...")
                await trio.sleep(3)
    return wrapper


@relaunch_on_disconnect
async def send_updates(server_address, receive_channel):
    async with open_websocket_url(server_address) as ws:
        logger.info("Соединение установлено")
        async for route in receive_channel:
            await ws.send_message(route)


async def main():
    parser = bus_parser()
    parsed_args = parser.parse_args()

    server_url = parsed_args.server
    routes_number = parsed_args.routes_number
    buses_on_route = parsed_args.buses_on_route
    websockets_number = parsed_args.websockets_number
    refresh_timeout = parsed_args.refresh_timeout
    log = parsed_args.l

    delay = 1
    if log:
        logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

    send_channels = []
    receive_channels = []

    try:
        async with trio.open_nursery() as nursery:

            for _ in range(websockets_number):
                send_channel, receive_channel = trio.open_memory_channel(0)
                send_channels.append(send_channel)
                receive_channels.append(receive_channel)

            for receive_channel in receive_channels:
                nursery.start_soon(send_updates, server_url, receive_channel)

            await trio.sleep(delay)

            routes = list(load_routes())
            for route in islice(routes, routes_number):
                for bus_idx in range(buses_on_route):
                    bus_id = generate_bus_id(route['name'], bus_idx)
                    channel = choice(send_channels)
                    nursery.start_soon(partial(run_bus, route, bus_id, channel, refresh_timeout))

    except* KeyboardInterrupt:
        logger.info("Программа остановлена пользователем")

    except* Exception as e:
        for exp in e.exceptions:
            logger.exception(f"Ошибка: {exp}")


if __name__ == "__main__":
    trio.run(main)
