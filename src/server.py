"""
TCP чат-сервер с поддержкой нескольких клиентов.

Функционал:
- Принимает подключения на указанном порту
- Поддерживает минимум 2 одновременных клиента
- Пересылает сообщения между клиентами
- Отправляет подтверждения о доставке
- Ведет логирование событий
"""

import socket
import threading
import logging
from queue import Queue

from src.settings import ALLOWED_COMMANDS


class ChatServer:
    def __init__(self, host='0.0.0.0', port=5555):
        """Инициализация сервера"""
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}  # {client_id: (conn, addr)}
        self.message_queues = {}  # {client_id: Queue}
        self.client_counter = 0
        self.lock = threading.Lock()

        # Настройка логирования
        logging.basicConfig(
            filename='server.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            encoding='utf-8'
        )

    def start(self):
        """Запуск сервера"""
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        logging.info(f'Сервер запущен на {self.host}:{self.port}')
        print(f'Сервер запущен на {self.host}:{self.port}')

        try:
            while True:
                conn, addr = self.server_socket.accept()
                self.client_counter += 1
                client_id = self.client_counter

                with self.lock:
                    self.clients[client_id] = (conn, addr)
                    self.message_queues[client_id] = Queue()

                logging.info(f'Новое подключение: {addr} (ID: {client_id})')
                print(f'Новое подключение: {addr} (ID: {client_id})')

                self.message_queues[client_id].put(
                    str(client_id)
                )

                # Запуск потоков для клиента
                threading.Thread(
                    target=self.handle_client,
                    args=(client_id,),
                    daemon=True
                ).start()

                threading.Thread(
                    target=self.send_messages,
                    args=(client_id,),
                    daemon=True
                ).start()

        except KeyboardInterrupt:
            self.shutdown()

    def handle_client(self, client_id):
        """Обработка входящих сообщений от клиента"""
        conn, addr = self.clients[client_id]

        try:
            while True:
                data = conn.recv(1024).decode('utf-8')
                if not data:
                    break

                logging.info(f'Получено от {addr} (ID: {client_id}): {data}')

                # Обработка сообщения
                if data.startswith('/send'):
                    parts = data.split(maxsplit=2)
                    if len(parts) == 3 and parts[1].isdigit():
                        recipient_id = int(parts[1])
                        message = parts[2]
                        self.route_message(client_id, recipient_id, message)
                    else:
                        self.message_queues[client_id].put(
                            'Ошибка: Неверный формат команды. Используйте /send <ID> <сообщение>'
                        )
                elif data.startswith('/users'):
                    self.message_queues[client_id].put(
                        'Список доступных пользователей: ' + ', '.join(str(x) for x in self.clients)
                    )
                else:
                    self.message_queues[client_id].put(
                        'Ошибка: Неизвестная команда. Список доступных команд:\n' + '\n'.join(ALLOWED_COMMANDS)
                    )

        except ConnectionResetError:
            pass
        finally:
            self.disconnect_client(client_id)

    def route_message(self, sender_id, recipient_id, message):
        """Маршрутизация сообщения к получателю"""
        with self.lock:
            if recipient_id in self.clients:
                self.message_queues[recipient_id].put(f'Сообщение от {sender_id}: {message}')
                self.message_queues[sender_id].put(f'Сообщение доставлено клиенту {recipient_id}')
                logging.info(f'Сообщение от {sender_id} доставлено клиенту {recipient_id}')
            else:
                self.message_queues[sender_id].put(f'Ошибка: Клиент {recipient_id} не найден')
                logging.warning(f'Попытка отправить сообщение несуществующему клиенту {recipient_id}')

    def send_messages(self, client_id):
        """Отправка сообщений клиенту из его очереди"""
        conn, _ = self.clients[client_id]

        try:
            while True:
                message = self.message_queues[client_id].get()
                conn.sendall(message.encode('utf-8'))
        except (ConnectionResetError, BrokenPipeError):
            self.disconnect_client(client_id)

    def disconnect_client(self, client_id):
        """Отключение клиента и очистка ресурсов"""
        with self.lock:
            if client_id in self.clients:
                conn, addr = self.clients.pop(client_id)
                self.message_queues.pop(client_id)
                conn.close()
                logging.info(f'Клиент {addr} (ID: {client_id}) отключен')
                print(f'Клиент {addr} (ID: {client_id}) отключен')

    def shutdown(self):
        """Корректное завершение работы сервера"""
        with self.lock:
            for client_id in list(self.clients.keys()):
                self.disconnect_client(client_id)
            self.server_socket.close()
            logging.info('Сервер остановлен')
            print('Сервер остановлен')


if __name__ == '__main__':
    server = ChatServer()
    server.start()