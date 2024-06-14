import socket
import pickle
import threading
import random
import time

# Константы
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 65432
BUFFER_SIZE = 131072

# Параметры карты
MAP_WIDTH = 4096
MAP_HEIGHT = 4096
PLAYER_SIZE = 30
RESOURCE_SIZE = 20
NUM_RESOURCES = 200
BLOCK_SIZE = 30
DYNAMITE_EXPLOSION_RADIUS = 60  # Радиус взрыва динамита

# Игроки, ресурсы и блоки
players = {}
resources = []
blocks = []
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]
available_colors = colors.copy()
lock = threading.Lock()

# Функция для генерации ресурсов
def generate_resources():
    global resources
    resources = [{'pos': [random.randint(0, MAP_WIDTH - RESOURCE_SIZE), random.randint(0, MAP_HEIGHT - RESOURCE_SIZE)], 'collected': False} for _ in range(NUM_RESOURCES)]
    print(f"Сгенерировано {NUM_RESOURCES} ресурсов")

# Проверка перекрытия блоков
def is_block_position_valid(block_pos):
    for block in blocks:
        if block['pos'] == block_pos:
            return False
    return True

# Функция для обработки взрыва динамита
def handle_dynamite_explosion(block_pos):
    global blocks, resources
    with lock:
        print(f"Динамит взорвался на позиции {block_pos}")
        for block in blocks[:]:
            if abs(block['pos'][0] - block_pos[0]) <= DYNAMITE_EXPLOSION_RADIUS and abs(block['pos'][1] - block_pos[1]) <= DYNAMITE_EXPLOSION_RADIUS:
                print(f"Блок на позиции {block['pos']} разрушен взрывом")
                blocks.remove(block)
                resources.append({'pos': block['pos'], 'collected': False})

# Обработчик клиентов
def handle_client(client_socket, client_address):
    global players, available_colors, resources, blocks
    player_id = client_address
    player_color = None
    
    try:
        with lock:
            if available_colors:
                player_color = available_colors.pop(0)
                player_id = len(players) + 1
                players[player_id] = {'pos': [MAP_WIDTH // 2, MAP_HEIGHT // 2], 'color': player_color, 'resources': 0}
                print(f"Игрок {player_id} подключен с цветом {player_color}")
            else:
                client_socket.close()
                return

        # Отправка начальных данных клиенту
        initial_data = {'id': player_id, 'color': player_color, 'map': {'width': MAP_WIDTH, 'height': MAP_HEIGHT}, 'resources': resources, 'blocks': blocks}
        client_socket.sendall(pickle.dumps(initial_data))

        while True:
            # Получение данных от клиента
            data = client_socket.recv(BUFFER_SIZE)
            if not data:
                break

            # Десериализация данных
            player_data = pickle.loads(data)
            player_pos = player_data.get('pos')
            block_pos = player_data.get('block_pos')
            block_type = player_data.get('block_type', 1)  # 1 - обычный блок, 2 - динамит

            with lock:
                if player_pos:
                    # Ограничение движения игрока границами карты
                    player_pos[0] = max(0, min(player_pos[0], MAP_WIDTH - PLAYER_SIZE))
                    player_pos[1] = max(0, min(player_pos[1], MAP_HEIGHT - PLAYER_SIZE))

                    # Обновление позиции игрока
                    players[player_id]['pos'] = player_pos

                    # Проверка на сбор ресурсов
                    for resource in resources:
                        if not resource['collected'] and abs(player_pos[0] - resource['pos'][0]) < RESOURCE_SIZE and abs(player_pos[1] - resource['pos'][1]) < RESOURCE_SIZE:
                            resource['collected'] = True
                            players[player_id]['resources'] += 1
                            print(f"Игрок {player_id} собрал ресурс на позиции {resource['pos']}")

                            # Если все ресурсы собраны, сгенерировать новые
                            if all(r['collected'] for r in resources):
                                generate_resources()

                if block_pos and players[player_id]['resources'] > 0:
                    # Выравнивание позиции блока по сетке
                    block_pos[0] = (block_pos[0] // BLOCK_SIZE) * BLOCK_SIZE
                    block_pos[1] = (block_pos[1] // BLOCK_SIZE) * BLOCK_SIZE

                    if is_block_position_valid(block_pos):
                        if block_type == 2:
                            # Добавление динамита и запуск таймера взрыва
                            blocks.append({'pos': block_pos, 'color': (255, 0, 0), 'type': 2})
                            threading.Timer(3.0, handle_dynamite_explosion, args=[block_pos]).start()
                            print(f"Игрок {player_id} разместил динамит на позиции {block_pos}")
                        else:
                            # Добавление обычного блока
                            blocks.append({'pos': block_pos, 'color': players[player_id]['color'], 'type': 1})
                            print(f"Игрок {player_id} разместил блок на позиции {block_pos}")
                        players[player_id]['resources'] -= 1

            # Отправка обновленных данных всем клиентам
            response = pickle.dumps({'players': players, 'resources': resources, 'blocks': blocks})
            client_socket.sendall(response)
    except:
        pass
    finally:
        with lock:
            if player_id in players:
                del players[player_id]
                available_colors.append(player_color)
                print(f"Игрок {player_id} отключен")
        client_socket.close()

# Создание сокета сервера
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((SERVER_HOST, SERVER_PORT))
server_socket.listen()

# Генерация ресурсов
generate_resources()

print(f"Сервер запущен на {SERVER_HOST}:{SERVER_PORT}")

while True:
    client_socket, client_address = server_socket.accept()
    print(f"Подключен клиент: {client_address}")
    client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
    client_thread.start()