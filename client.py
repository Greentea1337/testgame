import pygame
import socket
import pickle
import threading

# Инициализация Pygame
pygame.init()

# Константы
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLAYER_SIZE = 30
RESOURCE_SIZE = 20
BLOCK_SIZE = 30
BACKGROUND_COLOR = (0, 0, 0)
GRID_COLOR = (50, 50, 50)  # Цвет сетки
FPS = 144
PLAYER_SPEED = 300
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 65432
BUFFER_SIZE = 131072

# Цвета
DYNAMITE_COLOR = (255, 0, 0)

# Создание окна
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Квадратная игра")

# Игрок
player_id = None
player_pos = [SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2]
player_color = None
player_resources = 0

# Параметры карты
map_width = None
map_height = None

# Другие игроки, ресурсы и блоки
other_players = {}
resources = []
blocks = []

# Выбранный тип блока
selected_block_type = 1

# Функция для получения данных от сервера
def receive_data(client_socket):
    global other_players, player_color, player_id, map_width, map_height, resources, blocks, player_resources
    while True:
        try:
            data = client_socket.recv(BUFFER_SIZE)
            if data:
                server_data = pickle.loads(data)
                if player_id is None:
                    player_id = server_data['id']
                    player_color = server_data['color']
                    map_width = server_data['map']['width']
                    map_height = server_data['map']['height']
                    resources = server_data['resources']
                    blocks = server_data['blocks']
                else:
                    other_players = server_data['players']
                    resources = server_data['resources']
                    blocks = server_data['blocks']
                    player_resources = other_players[player_id]['resources']
        except:
            break

# Создание сокета клиента
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_HOST, SERVER_PORT))

# Запуск потока для получения данных от сервера
receive_thread = threading.Thread(target=receive_data, args=(client_socket,))
receive_thread.start()

# Функция проверки коллизий
def check_collision(new_pos):
    # Проверка коллизий с блоками и динамитом
    for block in blocks:
        if (new_pos[0] < block['pos'][0] + BLOCK_SIZE and
            new_pos[0] + PLAYER_SIZE > block['pos'][0] and
            new_pos[1] < block['pos'][1] + BLOCK_SIZE and
            new_pos[1] + PLAYER_SIZE > block['pos'][1]):
            return True
    return False

# Основной цикл игры
running = True
clock = pygame.time.Clock()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Обработка кликов мыши для размещения блоков
        if event.type == pygame.MOUSEBUTTONDOWN and player_resources > 0:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            block_x = mouse_x + player_pos[0] - SCREEN_WIDTH // 2
            block_y = mouse_y + player_pos[1] - SCREEN_HEIGHT // 2

            block_x = max(0, min(block_x, map_width - BLOCK_SIZE))
            block_y = max(0, min(block_y, map_height - BLOCK_SIZE))

            block_pos = [block_x, block_y]
            block_data = {'block_pos': block_pos, 'block_type': selected_block_type}
            client_socket.sendall(pickle.dumps(block_data))

        # Обработка нажатий клавиш для выбора типа блока
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                selected_block_type = 1
            elif event.key == pygame.K_2:
                selected_block_type = 2

    # Обработка нажатий клавиш для движения
    keys = pygame.key.get_pressed()
    delta_time = clock.get_time() / 1000

    new_pos = player_pos.copy()
    if keys[pygame.K_w]:
        new_pos[1] -= PLAYER_SPEED * delta_time
    if keys[pygame.K_s]:
        new_pos[1] += PLAYER_SPEED * delta_time
    if keys[pygame.K_a]:
        new_pos[0] -= PLAYER_SPEED * delta_time
    if keys[pygame.K_d]:
        new_pos[0] += PLAYER_SPEED * delta_time

    # Ограничение движения игрока границами карты
    if map_width is not None and map_height is not None:
        new_pos[0] = max(0, min(new_pos[0], map_width - PLAYER_SIZE))
        new_pos[1] = max(0, min(new_pos[1], map_height - PLAYER_SIZE))

    # Проверка коллизий и обновление позиции игрока
    if not check_collision(new_pos):
        player_pos = new_pos

    # Отправка данных на сервер
    if player_id is not None:
        player_data = {'id': player_id, 'pos': player_pos}
        client_socket.sendall(pickle.dumps(player_data))

    # Камера
    camera_x = player_pos[0] - SCREEN_WIDTH // 2
    camera_y = player_pos[1] - SCREEN_HEIGHT // 2

    # Отрисовка
    screen.fill(BACKGROUND_COLOR)

    # Отрисовка сетки
    if map_width is not None and map_height is not None:
        for x in range(0, map_width, BLOCK_SIZE):
            pygame.draw.line(screen, GRID_COLOR, (x - camera_x, 0 - camera_y), (x - camera_x, map_height - camera_y))
        for y in range(0, map_height, BLOCK_SIZE):
            pygame.draw.line(screen, GRID_COLOR, (0 - camera_x, y - camera_y), (map_width - camera_x, y - camera_y))

    if player_color:
        pygame.draw.rect(screen, player_color, (player_pos[0] - camera_x, player_pos[1] - camera_y, PLAYER_SIZE, PLAYER_SIZE))
    for pid, data in other_players.items():
        if pid != player_id:
            pygame.draw.rect(screen, data['color'], (data['pos'][0] - camera_x, data['pos'][1] - camera_y, PLAYER_SIZE, PLAYER_SIZE))
    
    # Отрисовка ресурсов
    for resource in resources:
        if not resource['collected']:
            pygame.draw.rect(screen, (255, 255, 0), (resource['pos'][0] - camera_x, resource['pos'][1] - camera_y, RESOURCE_SIZE, RESOURCE_SIZE))

    # Отрисовка блоков
    for block in blocks:
        block_color = DYNAMITE_COLOR if block['type'] == 2 else block['color']
        pygame.draw.rect(screen, block_color, (block['pos'][0] - camera_x, block['pos'][1] - camera_y, BLOCK_SIZE, BLOCK_SIZE))

    # Отрисовка границ карты
    if map_width is not None and map_height is not None:
        pygame.draw.rect(screen, (255, 255, 255), (0 - camera_x, 0 - camera_y, map_width, map_height), 2)

    pygame.display.flip()

    # Ограничение FPS
    clock.tick(FPS)

# Завершение Pygame
pygame.quit()
client_socket.close()