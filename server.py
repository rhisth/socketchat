import socket
import threading
import os
from datetime import datetime
from time import sleep

from config import hostname, port

class Logger:
    def __init__(self, path):
        self.format = ".txt"
        self.filename = datetime.now().strftime('%Y-%m-%d %H-%M-%S') + self.format
        self.path = path

    def check_path(self):
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def write(self, text):
        self.check_path()
        with open(f"{self.path}/{self.filename}", "a", encoding="utf-8") as file:
            file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: " + text + "\n")

class Server:
    def __init__(self, hostname, port, logger=None):
        self.hostname = hostname
        self.port = port
        self.logger = logger
        self.clients = []
        self.rooms = []
        self.lastroomid = 0

    def get_room(self, id):
        for room in self.rooms:
            if id == room.id:
                return room

    def create_room(self, name):
        self.lastroomid += 1
        room = Room(self.lastroomid, name=name)
        self.rooms.append(room)
        return room

    def delete_room(self, id):
        room = self.get_room(id)
        room.broadcast("Комната была удалена сервером.")
        for client in room.clients:
            client.room = None
        self.rooms.remove(room)

    def broadcast(self, message):
        for client in self.clients:
            client.send(message)

    def log(self, text):
        if self.logger:
            self.logger.write(text)

    def start(self):
        server = socket.socket()
        try:
            server.bind((self.hostname, self.port))
        except OSError:
            self.log("На этом адресе уже запущен сервер.")
            return
        server.listen()
        self.log("Сервер запустился.")
        while True:
            connection, address = server.accept()
            client = Client(connection, address, self)
            client.start()

class Room:
    def __init__(self, id, name=None):
        self.id = id
        self.name = name
        self.clients = []

    def broadcast(self, message):
        for client in self.clients:
            client.send(message)

class Client:
    def __init__(self, connection, address, server, nickname=None):
        self.connection = connection
        self.address = address
        self.server = server
        self.room = None
        self.nickname = nickname

    def command(self, data):
        if data == "/roomlist":
            if self.server.rooms:
                message = "Список комнат:"
                for room in self.server.rooms:
                    message += f'\nНазвание: "{room.name}". Айди: {room.id}. Участники: {len(room.clients)}.'
                self.send(message)
            else:
                self.send("На сервере нет каких-либо комнат.")
        elif data.startswith("/roomconnect "):
            try:
                id = int(data.split(" ", 1)[1])
            except ValueError:
                self.send("Айди должен быть в формате числа.")
            else:
                self.join(id)
        elif data == "/roomleave":
            if not self.leave():
                self.send("Вы не находитесь в какой-либо комнате.")
        elif data.startswith("/roomcreate "):
            id = self.server.create_room(data.split(" ", 1)[1]).id
            self.join(id)
        elif data == "/roommembers":
            if self.room:
                message = "Список участников комнаты:"
                for client in self.room.clients:
                    message += f'\nИмя: "{client.nickname}"'
                self.send(message)
            else:
                self.send("Вы не находитесь в какой-либо комнате.")
        elif data.startswith("/roomdelete "):
            try:
                id = int(data.split(" ", 1)[1])
            except ValueError:
                self.send("Айди должен быть в формате числа.")
            else:
                room = self.server.get_room(id)
                if room.clients:
                    self.send("Нельзя удалить комнату, где находятся люди.")
                else:
                    self.server.delete_room(id)
        else:
            return False
        return True

    def get_nickname(self):
        try:
            data = self.connection.recv(1024)
        except ConnectionResetError:
            self.disconnect()
        else:
            self.nickname = data.decode()
            return True
        return False

    def listen(self):
        self.server.log(f"Новое подключение: {self.address}.")
        if not self.get_nickname():
            return
        self.server.clients.append(self)
        self.server.log(f"Подключение к серверу: {self.address}. Никнейм: {self.nickname}.")
        while True:
            try:
                data = self.connection.recv(1024).decode()
            except ConnectionResetError:
                self.disconnect()
                return
            if data == "/quit":
                self.disconnect()
                return
            if not self.command(data):
                self.say(f"{self.nickname}: {data}")

    def say(self, message):
        if self.room:
            for client in self.room.clients:
                if self.connection != client.connection:
                    client.send(message)

    def send(self, data):
        self.connection.send(data.encode())

    def join(self, id):
        self.leave()
        room = self.server.get_room(id)
        room.clients.append(self)
        self.room = room
        self.room.broadcast(f"{self.nickname} присоединился к чату.")

    def disconnect(self):
        self.connection.close()
        self.server.log(f"Клиент {self.address} отключился. Никнейм: {self.nickname}.")
        self.leave()
        if self in self.server.clients:
            self.server.clients.remove(self)

    def leave(self):
        if self.room:
            self.room.clients.remove(self)
            self.room.broadcast(f"{self.nickname} вышел из чата.")
            self.room = None
            return True
        return False

    def start(self):
        self.thread = threading.Thread(target=self.listen, daemon=True)
        self.thread.start()

def main():
    logger = Logger("./logs")
    server = Server(hostname, port, logger=logger)
    server.start()

if __name__ == "__main__":
    main()
