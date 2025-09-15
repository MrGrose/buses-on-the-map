import argparse
import json
import os


def load_routes(directory_path='routes'):
    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            filepath = os.path.join(directory_path, filename)
            with open(filepath, 'r', encoding='utf8') as file:
                yield json.load(file)


def bus_parser():
    parser = argparse.ArgumentParser(description="Параметры для отображение автобусов")
    parser.add_argument("-s", "--server", default="ws://127.0.0.1:8080", help="адрес сервера")
    parser.add_argument("-r", "--routes_number", type=int, default=20, help="количество маршрутов")
    parser.add_argument("-b", "--buses_on_route", type=int, default=5, help="количество автобусов на каждом маршруте")
    parser.add_argument("-w", "--websockets_number", type=int, default=5, help="количество открытых веб-сокетов")
    parser.add_argument("-t", "--refresh_timeout", type=float, default=0.5, help="задержка в обновлении координат сервера")
    parser.add_argument("-l", action="store_false", help="настройка логирования")

    return parser


def server_parser():
    parser = argparse.ArgumentParser(description="Отображение транспорта в браузере")
    parser.add_argument("-t", "--refresh_timeout", type=float, default=0.5, help="задержка в обновлении координат сервера")
    parser.add_argument("-p", "--bus_port", type=int, default=8080, help="порт для имитатора автобусов")
    parser.add_argument("-br", "--browser_port", type=int, default=8000, help="порт для браузера")
    parser.add_argument("-bh", "--browser_host", type=str, default="127.0.0.1", help="хост для браузера")
    parser.add_argument("-l", action="store_false", help="настройка логирования")

    return parser


def generate_bus_id(route_id, bus_index):
    return f"{route_id}-{bus_index}"
