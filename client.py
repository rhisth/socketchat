import socket
import threading
import os
from time import sleep

from config import hostname, port

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def listen(connection):
    while True:
        try:
            data = connection.recv(1024)
        except ConnectionResetError:
            print("Оборвалось подключение с сервером.")
            connection.close()
            return
        except ConnectionAbortedError:
            print("Сервер закрыл подключение.")
            connection.close()
            return
        if data:
            print(data.decode())

def input_message(connection):
    while True:
        message = input()
        if message == "/close":
            connection.close()
            break
        try:
            connection.sendall(message.encode())
        except ConnectionResetError:
            clear()
            return

def input_name():
    name = None
    while not name:
        name = input("Введите никнейм: ")
    return name

def main():
    clear()
    name = input("Введите никнейм: ")
    client = socket.socket()
    try:
        client.connect((hostname, port))
    except ConnectionRefusedError:
        print("Не удалось подключиться к серверу.")
        client.close()
        return
    client.send(name.encode())
    print(f"Успешное подключение к серверу {hostname}:{port}.")
    thread = threading.Thread(target=listen, args=(client,), daemon=True)
    thread.start()
    input_message(client)

if __name__ == "__main__":
    main()
