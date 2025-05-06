"""
TCP чат-клиент.

Функционал:
- Подключается к серверу
- Отправляет сообщения
- Получает сообщения от сервера
- Получает подтверждения о доставке
"""

import socket
import threading
import argparse

from src.settings import ALLOWED_COMMANDS


class ChatClient:
    def __init__(self, host='localhost', port=5555):
        """Инициализация клиента"""
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = False
        self.client_id = None

    def connect(self):
        """Подключение к серверу"""
        try:
            print(f'Подключение к серверу {args.host}:{args.port}...')
            self.client_socket.connect((self.host, self.port))
            self.running = True

            # Получаем ID от сервера (первое сообщение)
            self.client_id = int(self.client_socket.recv(1024).decode('utf-8'))
            print(f'Подключено к серверу. Ваш ID: {self.client_id}')
            print('Доступные команды:', *ALLOWED_COMMANDS, sep='\n')

            # Запуск потока для получения сообщений
            threading.Thread(
                target=self.receive_messages,
                daemon=True
            ).start()

            self.send_messages()

        except ConnectionRefusedError:
            print('Не удалось подключиться к серверу')
        except KeyboardInterrupt:
            self.disconnect()

    def receive_messages(self):
        """Получение сообщений от сервера"""
        while self.running:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if not message:
                    break
                print(f'\n{message}\n>>> ', end='')
            except ConnectionResetError:
                break

        print("\nСоединение с сервером разорвано")
        self.running = False

    def send_messages(self):
        """Отправка сообщений на сервер"""
        try:
            while self.running:
                message = input('>>> ')
                if message.lower() in ('/exit', '/quit'):
                    break
                elif message.lower() == '/help':
                    print('Доступные команды:', *ALLOWED_COMMANDS, sep='\n')
                else:
                    self.client_socket.sendall(message.encode('utf-8'))
        except KeyboardInterrupt:
            pass
        finally:
            self.disconnect()

    def disconnect(self):
        """Отключение от сервера"""
        if self.running:
            self.running = False
            self.client_socket.close()
            print('Отключено от сервера')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TCP Chat Client')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=5555, help='Server port')

    args = parser.parse_args()

    client = ChatClient(args.host, args.port)
    client.connect()