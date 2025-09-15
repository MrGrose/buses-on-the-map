import json
import logging
from dataclasses import asdict, dataclass, field
from functools import partial
from typing import Optional

import trio
from pydantic import BaseModel, Field, ValidationError, field_validator
from trio_websocket import ConnectionClosed, serve_websocket

from utils import server_parser

logger = logging.getLogger("server")
logging.getLogger("trio-websocket").propagate = False


@dataclass
class Bus:
    busId: str
    lat: float
    lng: float
    route: str


@dataclass
class BusRoutes:
    buses: dict[str, Bus] = field(default_factory=dict)


@dataclass
class WindowBounds:
    south_lat: float = 0
    north_lat: float = 0
    west_lng: float = 0
    east_lng: float = 0

    def is_inside(self, lat, lng):
        if self.south_lat < lat < self.north_lat and self.west_lng < lng < self.east_lng:
            return True
        return False

    def update(self, south_lat, north_lat, west_lng, east_lng):
        self.south_lat = south_lat
        self.north_lat = north_lat
        self.west_lng = west_lng
        self.east_lng = east_lng


class BusSchema(BaseModel):
    busId: str
    lat: float
    lng: float
    route: str


class BusRoutesSchema(BaseModel):
    buses: list[Bus] = Field(default_factory=list)


class WindowBoundsSchema(BaseModel):
    south_lat: float
    north_lat: float
    west_lng: float
    east_lng: float

    @field_validator("south_lat", "north_lat")
    @classmethod
    def check_latitude(cls, v):
        if not (-90 <= v <= 90):
            raise ValueError("Широта должна быть между -90 и 90")
        return v

    @field_validator("west_lng", "east_lng")
    @classmethod
    def check_longitude(cls, v):
        if not (-180 <= v <= 180):
            raise ValueError("Долгота должна быть между -180 и 180")
        return v


class InputWindowBoundsSchema(BaseModel):
    msgType: Optional[str] = None
    coor: WindowBoundsSchema


async def server(request, buses):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            bus_route = BusRoutesSchema.model_validate_json(message)

            if not bus_route.buses:
                await ws.send_message(json.dumps({"errors": ["Requires busId specified"], "msgType": "Errors"}, ensure_ascii=False))
                continue

            for bus in bus_route.buses:
                buses.buses[bus.busId] = bus

        except ValidationError:
            await ws.send_message(json.dumps({"errors": ["Requires valid JSON"], "msgType": "Errors"}))
            continue

        except ConnectionClosed:
            logger.info("Соединение закрыто")
            break


async def talk_to_browser(request, refresh_timeout, bounds, buses):
    ws = await request.accept()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(listen_browser, ws, bounds)
        while True:
            try:
                visible_buses = await send_buses(bounds, buses)
                if visible_buses:
                    await ws.send_message(json.dumps({"msgType": "Buses", "buses": visible_buses}, ensure_ascii=False))
                await trio.sleep(refresh_timeout)
            except ConnectionClosed:
                logger.info("Соединение закрыто")
                break


async def send_buses(bounds, buses):
    visible_buses = []
    for bus in buses.buses.values():
        if bounds.is_inside(bus.lat, bus.lng):
            visible_buses.append(asdict(bus))
    return visible_buses


async def listen_browser(ws, bounds):
    while True:
        try:
            message = await ws.get_message()
            listen_msg = InputWindowBoundsSchema.model_validate_json(message)

            if not listen_msg.msgType or listen_msg.msgType != "newBounds":
                await ws.send_message(json.dumps({"errors": ["Requires msgType specified"], "msgType": "Errors"}))
                continue

            bounds.update(listen_msg.data.south_lat, listen_msg.data.north_lat, listen_msg.data.west_lng, listen_msg.data.east_lng)

        except ValidationError:
            await ws.send_message(json.dumps({"errors": ["Requires valid JSON"], "msgType": "Errors"}))
            continue

        except ConnectionClosed:
            logger.info("Соединение закрыто")
            break


async def main():
    parser = server_parser()
    parsed_args = parser.parse_args()

    refresh_timeout = parsed_args.refresh_timeout
    bus_port = parsed_args.bus_port
    browser_port = parsed_args.browser_port
    host = parsed_args.browser_host
    log = parsed_args.l

    bounds = WindowBounds()
    buses = BusRoutes()

    if log:
        logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG)

    try:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(partial(serve_websocket, partial(server, buses=buses), host, bus_port, ssl_context=None))
            talk_to_brw = partial(talk_to_browser, refresh_timeout=refresh_timeout, bounds=bounds, buses=buses)
            nursery.start_soon(partial(serve_websocket, talk_to_brw, host, browser_port, ssl_context=None))

    except* KeyboardInterrupt:
        logger.info("Программа остановлена пользователем")

    except* Exception as e:
        for exp in e.exceptions:
            logger.exception(f"Ошибка: {exp}")


if __name__ == "__main__":
    trio.run(main)

































