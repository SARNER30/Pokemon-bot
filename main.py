import os
import random
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from keep_alive import keep_alive

TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_IDS = [5953677116]  # Ваш Telegram ID
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

# База данных
conn = sqlite3.connect('pokemon.db', check_same_thread=False)
cursor = conn.cursor()

# Инициализация БД
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                (user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 3000,
                pokeballs INTEGER DEFAULT 5,
                total_pokemons INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT FALSE,
                trainer_id INTEGER DEFAULT NULL,
                trainer_level INTEGER DEFAULT 1)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS pokemons
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                pokemon_id INTEGER,
                name TEXT,
                image TEXT,
                hp INTEGER,
                attack INTEGER,
                defense INTEGER,
                is_custom BOOLEAN DEFAULT FALSE,
                FOREIGN KEY(owner_id) REFERENCES users(user_id))''')

cursor.execute('''CREATE TABLE IF NOT EXISTS pokemon_counts
                (user_id INTEGER,
                pokemon_id INTEGER,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, pokemon_id))''')

cursor.execute('''CREATE TABLE IF NOT EXISTS custom_pokemons
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                image TEXT,
                hp INTEGER,
                attack INTEGER,
                defense INTEGER)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS trainers
                (id INTEGER PRIMARY KEY,
                name TEXT,
                price INTEGER,
                income INTEGER,
                image TEXT)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS pokedex
                (user_id INTEGER,
                pokemon_id INTEGER,
                seen BOOLEAN DEFAULT FALSE,
                caught BOOLEAN DEFAULT FALSE,
                PRIMARY KEY (user_id, pokemon_id))''')

# Заполняем тренеров
cursor.execute("SELECT COUNT(*) FROM trainers")
if cursor.fetchone()[0] == 0:
    TRAINERS = [
        (1, "Брок", 10000, 100, "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/trainer/1.png"),
        (2, "Мсти", 25000, 250, "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/trainer/2.png"),
        (3, "Эш", 50000, 500, "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/trainer/3.png")
    ]
    cursor.executemany("INSERT INTO trainers VALUES (?, ?, ?, ?, ?)", TRAINERS)
    conn.commit()

# Главное меню
def get_main_menu(user_id):
    buttons = [
        [KeyboardButton(text="🎣 Ловить покемона")],
        [KeyboardButton(text="📊 Моя статистика")],
        [KeyboardButton(text="📦 Мои покемоны")],
        [KeyboardButton(text="🛒 Магазин")],
        [KeyboardButton(text="📘 Покедекс")]
    ]
    if user_id in ADMIN_IDS:
        buttons.append([KeyboardButton(text="👑 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# Админ-меню
def get_admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать покемона")],
            [KeyboardButton(text="Изменить баланс")],
            [KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True
    )

# Магазин
def get_shop_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎣 Купить покебал (500)")],
            [KeyboardButton(text="👨‍🏫 Нанять тренера")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

# Покемоны (первые 50 для примера)
POKEMONS = {
    1: [
    {"id": 1, "name": "Bulbasaur", "hp": 45, "attack": 49, "defense": 49, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/1.png"},
    {"id": 2, "name": "Ivysaur", "hp": 60, "attack": 62, "defense": 63, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/2.png"},
    {"id": 3, "name": "Venusaur", "hp": 80, "attack": 82, "defense": 83, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/3.png"},
    {"id": 4, "name": "Charmander", "hp": 39, "attack": 52, "defense": 43, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/4.png"},
    {"id": 5, "name": "Charmeleon", "hp": 58, "attack": 64, "defense": 58, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/5.png"},
    {"id": 6, "name": "Charizard", "hp": 78, "attack": 84, "defense": 78, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/6.png"},
    {"id": 7, "name": "Squirtle", "hp": 44, "attack": 48, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/7.png"},
    {"id": 8, "name": "Wartortle", "hp": 59, "attack": 63, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/8.png"},
    {"id": 9, "name": "Blastoise", "hp": 79, "attack": 83, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/9.png"},
    {"id": 10, "name": "Caterpie", "hp": 45, "attack": 30, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/10.png"},
    {"id": 11, "name": "Metapod", "hp": 50, "attack": 20, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/11.png"},
    {"id": 12, "name": "Butterfree", "hp": 60, "attack": 45, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/12.png"},
    {"id": 13, "name": "Weedle", "hp": 40, "attack": 35, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/13.png"},
    {"id": 14, "name": "Kakuna", "hp": 45, "attack": 25, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/14.png"},
    {"id": 15, "name": "Beedrill", "hp": 65, "attack": 90, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/15.png"},
    {"id": 16, "name": "Pidgey", "hp": 40, "attack": 45, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/16.png"},
    {"id": 17, "name": "Pidgeotto", "hp": 63, "attack": 60, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/17.png"},
    {"id": 18, "name": "Pidgeot", "hp": 83, "attack": 80, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/18.png"},
    {"id": 19, "name": "Rattata", "hp": 30, "attack": 56, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/19.png"},
    {"id": 20, "name": "Raticate", "hp": 55, "attack": 81, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/20.png"},
    {"id": 21, "name": "Spearow", "hp": 40, "attack": 60, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/21.png"},
    {"id": 22, "name": "Fearow", "hp": 65, "attack": 90, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/22.png"},
    {"id": 23, "name": "Ekans", "hp": 35, "attack": 60, "defense": 44, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/23.png"},
    {"id": 24, "name": "Arbok", "hp": 60, "attack": 85, "defense": 69, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/24.png"},
    {"id": 25, "name": "Pikachu", "hp": 35, "attack": 55, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/25.png"},
    {"id": 26, "name": "Raichu", "hp": 60, "attack": 90, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/26.png"},
    {"id": 27, "name": "Sandshrew", "hp": 50, "attack": 75, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/27.png"},
    {"id": 28, "name": "Sandslash", "hp": 75, "attack": 100, "defense": 110, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/28.png"},
    {"id": 29, "name": "Nidoran♀", "hp": 55, "attack": 47, "defense": 52, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/29.png"},
    {"id": 30, "name": "Nidorina", "hp": 70, "attack": 62, "defense": 67, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/30.png"},
    {"id": 31, "name": "Nidoqueen", "hp": 90, "attack": 92, "defense": 87, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/31.png"},
    {"id": 32, "name": "Nidoran♂", "hp": 46, "attack": 57, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/32.png"},
    {"id": 33, "name": "Nidorino", "hp": 61, "attack": 72, "defense": 57, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/33.png"},
    {"id": 34, "name": "Nidoking", "hp": 81, "attack": 102, "defense": 77, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/34.png"},
    {"id": 35, "name": "Clefairy", "hp": 70, "attack": 45, "defense": 48, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/35.png"},
    {"id": 36, "name": "Clefable", "hp": 95, "attack": 70, "defense": 73, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/36.png"},
    {"id": 37, "name": "Vulpix", "hp": 38, "attack": 41, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/37.png"},
    {"id": 38, "name": "Ninetales", "hp": 73, "attack": 76, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/38.png"},
    {"id": 39, "name": "Jigglypuff", "hp": 115, "attack": 45, "defense": 20, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/39.png"},
    {"id": 40, "name": "Wigglytuff", "hp": 140, "attack": 70, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/40.png"},
    {"id": 41, "name": "Zubat", "hp": 40, "attack": 45, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/41.png"},
    {"id": 42, "name": "Golbat", "hp": 75, "attack": 80, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/42.png"},
    {"id": 43, "name": "Oddish", "hp": 45, "attack": 50, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/43.png"},
    {"id": 44, "name": "Gloom", "hp": 60, "attack": 65, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/44.png"},
    {"id": 45, "name": "Vileplume", "hp": 75, "attack": 80, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/45.png"},
    {"id": 46, "name": "Paras", "hp": 35, "attack": 70, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/46.png"},
    {"id": 47, "name": "Parasect", "hp": 60, "attack": 95, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/47.png"},
    {"id": 48, "name": "Venonat", "hp": 60, "attack": 55, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/48.png"},
    {"id": 49, "name": "Venomoth", "hp": 70, "attack": 65, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/49.png"},
    {"id": 50, "name": "Diglett", "hp": 10, "attack": 55, "defense": 25, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/50.png"},
    {"id": 51, "name": "Dugtrio", "hp": 35, "attack": 100, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/51.png"},
    {"id": 52, "name": "Meowth", "hp": 40, "attack": 45, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/52.png"},
    {"id": 53, "name": "Persian", "hp": 65, "attack": 70, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/53.png"},
    {"id": 54, "name": "Psyduck", "hp": 50, "attack": 52, "defense": 48, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/54.png"},
    {"id": 55, "name": "Golduck", "hp": 80, "attack": 82, "defense": 78, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/55.png"},
    {"id": 56, "name": "Mankey", "hp": 40, "attack": 80, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/56.png"},
    {"id": 57, "name": "Primeape", "hp": 65, "attack": 105, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/57.png"},
    {"id": 58, "name": "Growlithe", "hp": 55, "attack": 70, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/58.png"},
    {"id": 59, "name": "Arcanine", "hp": 90, "attack": 110, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/59.png"},
    {"id": 60, "name": "Poliwag", "hp": 40, "attack": 50, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/60.png"},
    {"id": 61, "name": "Poliwhirl", "hp": 65, "attack": 65, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/61.png"},
    {"id": 62, "name": "Poliwrath", "hp": 90, "attack": 95, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/62.png"},
    {"id": 63, "name": "Abra", "hp": 25, "attack": 20, "defense": 15, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/63.png"},
    {"id": 64, "name": "Kadabra", "hp": 40, "attack": 35, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/64.png"},
    {"id": 65, "name": "Alakazam", "hp": 55, "attack": 50, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/65.png"},
    {"id": 66, "name": "Machop", "hp": 70, "attack": 80, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/66.png"},
    {"id": 67, "name": "Machoke", "hp": 80, "attack": 100, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/67.png"},
    {"id": 68, "name": "Machamp", "hp": 90, "attack": 130, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/68.png"},
    {"id": 69, "name": "Bellsprout", "hp": 50, "attack": 75, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/69.png"},
    {"id": 70, "name": "Weepinbell", "hp": 65, "attack": 90, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/70.png"},
    {"id": 71, "name": "Victreebel", "hp": 80, "attack": 105, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/71.png"},
    {"id": 72, "name": "Tentacool", "hp": 40, "attack": 40, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/72.png"},
    {"id": 73, "name": "Tentacruel", "hp": 80, "attack": 70, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/73.png"},
    {"id": 74, "name": "Geodude", "hp": 40, "attack": 80, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/74.png"},
    {"id": 75, "name": "Graveler", "hp": 55, "attack": 95, "defense": 115, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/75.png"},
    {"id": 76, "name": "Golem", "hp": 80, "attack": 120, "defense": 130, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/76.png"},
    {"id": 77, "name": "Ponyta", "hp": 50, "attack": 85, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/77.png"},
    {"id": 78, "name": "Rapidash", "hp": 65, "attack": 100, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/78.png"},
    {"id": 79, "name": "Slowpoke", "hp": 90, "attack": 65, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/79.png"},
    {"id": 80, "name": "Slowbro", "hp": 95, "attack": 75, "defense": 110, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/80.png"},
    {"id": 81, "name": "Magnemite", "hp": 25, "attack": 35, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/81.png"},
    {"id": 82, "name": "Magneton", "hp": 50, "attack": 60, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/82.png"},
    {"id": 83, "name": "Farfetch'd", "hp": 52, "attack": 90, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/83.png"},
    {"id": 84, "name": "Doduo", "hp": 35, "attack": 85, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/84.png"},
    {"id": 85, "name": "Dodrio", "hp": 60, "attack": 110, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/85.png"},
    {"id": 86, "name": "Seel", "hp": 65, "attack": 45, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/86.png"},
    {"id": 87, "name": "Dewgong", "hp": 90, "attack": 70, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/87.png"},
    {"id": 88, "name": "Grimer", "hp": 80, "attack": 80, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/88.png"},
    {"id": 89, "name": "Muk", "hp": 105, "attack": 105, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/89.png"},
    {"id": 90, "name": "Shellder", "hp": 30, "attack": 65, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/90.png"},
    {"id": 91, "name": "Cloyster", "hp": 50, "attack": 95, "defense": 180, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/91.png"},
    {"id": 92, "name": "Gastly", "hp": 30, "attack": 35, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/92.png"},
    {"id": 93, "name": "Haunter", "hp": 45, "attack": 50, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/93.png"},
    {"id": 94, "name": "Gengar", "hp": 60, "attack": 65, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/94.png"},
    {"id": 95, "name": "Onix", "hp": 35, "attack": 45, "defense": 160, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/95.png"},
    {"id": 96, "name": "Drowzee", "hp": 60, "attack": 48, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/96.png"},
    {"id": 97, "name": "Hypno", "hp": 85, "attack": 73, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/97.png"},
    {"id": 98, "name": "Krabby", "hp": 30, "attack": 105, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/98.png"},
    {"id": 99, "name": "Kingler", "hp": 55, "attack": 130, "defense": 115, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/99.png"},
    {"id": 100, "name": "Voltorb", "hp": 40, "attack": 30, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/100.png"}
].
    2: [
    {"id": 101, "name": "Electrode", "hp": 60, "attack": 50, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/101.png"},
    {"id": 102, "name": "Exeggcute", "hp": 60, "attack": 40, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/102.png"},
    {"id": 103, "name": "Exeggutor", "hp": 95, "attack": 95, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/103.png"},
    {"id": 104, "name": "Cubone", "hp": 50, "attack": 50, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/104.png"},
    {"id": 105, "name": "Marowak", "hp": 60, "attack": 80, "defense": 110, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/105.png"},
    {"id": 106, "name": "Hitmonlee", "hp": 50, "attack": 120, "defense": 53, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/106.png"},
    {"id": 107, "name": "Hitmonchan", "hp": 50, "attack": 105, "defense": 79, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/107.png"},
    {"id": 108, "name": "Lickitung", "hp": 90, "attack": 55, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/108.png"},
    {"id": 109, "name": "Koffing", "hp": 40, "attack": 65, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/109.png"},
    {"id": 110, "name": "Weezing", "hp": 65, "attack": 90, "defense": 120, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/110.png"},
    {"id": 111, "name": "Rhyhorn", "hp": 80, "attack": 85, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/111.png"},
    {"id": 112, "name": "Rhydon", "hp": 105, "attack": 130, "defense": 120, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/112.png"},
    {"id": 113, "name": "Chansey", "hp": 250, "attack": 5, "defense": 5, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/113.png"},
    {"id": 114, "name": "Tangela", "hp": 65, "attack": 55, "defense": 115, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/114.png"},
    {"id": 115, "name": "Kangaskhan", "hp": 105, "attack": 95, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/115.png"},
    {"id": 116, "name": "Horsea", "hp": 30, "attack": 40, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/116.png"},
    {"id": 117, "name": "Seadra", "hp": 55, "attack": 65, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/117.png"},
    {"id": 118, "name": "Goldeen", "hp": 45, "attack": 67, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/118.png"},
    {"id": 119, "name": "Seaking", "hp": 80, "attack": 92, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/119.png"},
    {"id": 120, "name": "Staryu", "hp": 30, "attack": 45, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/120.png"},
    {"id": 121, "name": "Starmie", "hp": 60, "attack": 75, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/121.png"},
    {"id": 122, "name": "Mr. Mime", "hp": 40, "attack": 45, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/122.png"},
    {"id": 123, "name": "Scyther", "hp": 70, "attack": 110, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/123.png"},
    {"id": 124, "name": "Jynx", "hp": 65, "attack": 50, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/124.png"},
    {"id": 125, "name": "Electabuzz", "hp": 65, "attack": 83, "defense": 57, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/125.png"},
    {"id": 126, "name": "Magmar", "hp": 65, "attack": 95, "defense": 57, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/126.png"},
    {"id": 127, "name": "Pinsir", "hp": 65, "attack": 125, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/127.png"},
    {"id": 128, "name": "Tauros", "hp": 75, "attack": 100, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/128.png"},
    {"id": 129, "name": "Magikarp", "hp": 20, "attack": 10, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/129.png"},
    {"id": 130, "name": "Gyarados", "hp": 95, "attack": 125, "defense": 79, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/130.png"},
    {"id": 131, "name": "Lapras", "hp": 130, "attack": 85, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/131.png"},
    {"id": 132, "name": "Ditto", "hp": 48, "attack": 48, "defense": 48, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/132.png"},
    {"id": 133, "name": "Eevee", "hp": 55, "attack": 55, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/133.png"},
    {"id": 134, "name": "Vaporeon", "hp": 130, "attack": 65, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/134.png"},
    {"id": 135, "name": "Jolteon", "hp": 65, "attack": 65, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/135.png"},
    {"id": 136, "name": "Flareon", "hp": 65, "attack": 130, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/136.png"},
    {"id": 137, "name": "Porygon", "hp": 65, "attack": 60, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/137.png"},
    {"id": 138, "name": "Omanyte", "hp": 35, "attack": 40, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/138.png"},
    {"id": 139, "name": "Omastar", "hp": 70, "attack": 60, "defense": 125, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/139.png"},
    {"id": 140, "name": "Kabuto", "hp": 30, "attack": 80, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/140.png"},
    {"id": 141, "name": "Kabutops", "hp": 60, "attack": 115, "defense": 105, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/141.png"},
    {"id": 142, "name": "Aerodactyl", "hp": 80, "attack": 105, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/142.png"},
    {"id": 143, "name": "Snorlax", "hp": 160, "attack": 110, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/143.png"},
    {"id": 144, "name": "Articuno", "hp": 90, "attack": 85, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/144.png"},
    {"id": 145, "name": "Zapdos", "hp": 90, "attack": 90, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/145.png"},
    {"id": 146, "name": "Moltres", "hp": 90, "attack": 100, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/146.png"},
    {"id": 147, "name": "Dratini", "hp": 41, "attack": 64, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/147.png"},
    {"id": 148, "name": "Dragonair", "hp": 61, "attack": 84, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/148.png"},
    {"id": 149, "name": "Dragonite", "hp": 91, "attack": 134, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/149.png"},
    {"id": 150, "name": "Mewtwo", "hp": 106, "attack": 110, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/150.png"},
    {"id": 151, "name": "Mew", "hp": 100, "attack": 100, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/151.png"},
    {"id": 152, "name": "Chikorita", "hp": 45, "attack": 49, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/152.png"},
    {"id": 153, "name": "Bayleef", "hp": 60, "attack": 62, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/153.png"},
    {"id": 154, "name": "Meganium", "hp": 80, "attack": 82, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/154.png"},
    {"id": 155, "name": "Cyndaquil", "hp": 39, "attack": 52, "defense": 43, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/155.png"},
    {"id": 156, "name": "Quilava", "hp": 58, "attack": 64, "defense": 58, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/156.png"},
    {"id": 157, "name": "Typhlosion", "hp": 78, "attack": 84, "defense": 78, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/157.png"},
    {"id": 158, "name": "Totodile", "hp": 50, "attack": 65, "defense": 64, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/158.png"},
    {"id": 159, "name": "Croconaw", "hp": 65, "attack": 80, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/159.png"},
    {"id": 160, "name": "Feraligatr", "hp": 85, "attack": 105, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/160.png"},
    {"id": 161, "name": "Sentret", "hp": 35, "attack": 46, "defense": 34, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/161.png"},
    {"id": 162, "name": "Furret", "hp": 85, "attack": 76, "defense": 64, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/162.png"},
    {"id": 163, "name": "Hoothoot", "hp": 60, "attack": 30, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/163.png"},
    {"id": 164, "name": "Noctowl", "hp": 100, "attack": 50, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/164.png"},
    {"id": 165, "name": "Ledyba", "hp": 40, "attack": 20, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/165.png"},
    {"id": 166, "name": "Ledian", "hp": 55, "attack": 35, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/166.png"},
    {"id": 167, "name": "Spinarak", "hp": 40, "attack": 60, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/167.png"},
    {"id": 168, "name": "Ariados", "hp": 70, "attack": 90, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/168.png"},
    {"id": 169, "name": "Crobat", "hp": 85, "attack": 90, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/169.png"},
    {"id": 170, "name": "Chinchou", "hp": 75, "attack": 38, "defense": 38, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/170.png"},
    {"id": 171, "name": "Lanturn", "hp": 125, "attack": 58, "defense": 58, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/171.png"},
    {"id": 172, "name": "Pichu", "hp": 20, "attack": 40, "defense": 15, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/172.png"},
    {"id": 173, "name": "Cleffa", "hp": 50, "attack": 25, "defense": 28, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/173.png"},
    {"id": 174, "name": "Igglybuff", "hp": 90, "attack": 30, "defense": 15, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/174.png"},
    {"id": 175, "name": "Togepi", "hp": 35, "attack": 20, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/175.png"},
    {"id": 176, "name": "Togetic", "hp": 55, "attack": 40, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/176.png"},
    {"id": 177, "name": "Natu", "hp": 40, "attack": 50, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/177.png"},
    {"id": 178, "name": "Xatu", "hp": 65, "attack": 75, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/178.png"},
    {"id": 179, "name": "Mareep", "hp": 55, "attack": 40, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/179.png"},
    {"id": 180, "name": "Flaaffy", "hp": 70, "attack": 55, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/180.png"},
    {"id": 181, "name": "Ampharos", "hp": 90, "attack": 75, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/181.png"},
    {"id": 182, "name": "Bellossom", "hp": 75, "attack": 80, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/182.png"},
    {"id": 183, "name": "Marill", "hp": 70, "attack": 20, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/183.png"},
    {"id": 184, "name": "Azumarill", "hp": 100, "attack": 50, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/184.png"},
    {"id": 185, "name": "Sudowoodo", "hp": 70, "attack": 100, "defense": 115, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/185.png"},
    {"id": 186, "name": "Politoed", "hp": 90, "attack": 75, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/186.png"},
    {"id": 187, "name": "Hoppip", "hp": 35, "attack": 35, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/187.png"},
    {"id": 188, "name": "Skiploom", "hp": 55, "attack": 45, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/188.png"},
    {"id": 189, "name": "Jumpluff", "hp": 75, "attack": 55, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/189.png"},
    {"id": 190, "name": "Aipom", "hp": 55, "attack": 70, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/190.png"},
    {"id": 191, "name": "Sunkern", "hp": 30, "attack": 30, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/191.png"},
    {"id": 192, "name": "Sunflora", "hp": 75, "attack": 75, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/192.png"},
    {"id": 193, "name": "Yanma", "hp": 65, "attack": 65, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/193.png"},
    {"id": 194, "name": "Wooper", "hp": 55, "attack": 45, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/194.png"},
    {"id": 195, "name": "Quagsire", "hp": 95, "attack": 85, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/195.png"},
    {"id": 196, "name": "Espeon", "hp": 65, "attack": 65, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/196.png"},
    {"id": 197, "name": "Umbreon", "hp": 95, "attack": 65, "defense": 110, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/197.png"},
    {"id": 198, "name": "Murkrow", "hp": 60, "attack": 85, "defense": 42, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/198.png"},
    {"id": 199, "name": "Slowking", "hp": 95, "attack": 75, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/199.png"},
    {"id": 200, "name": "Misdreavus", "hp": 60, "attack": 60, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/200.png"}
],
3: [
{"id": 201, "name": "Unown", "hp": 48, "attack": 72, "defense": 48, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/201.png"},
{"id": 202, "name": "Wobbuffet", "hp": 190, "attack": 33, "defense": 58, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/202.png"},
{"id": 203, "name": "Girafarig", "hp": 70, "attack": 80, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/203.png"},
{"id": 204, "name": "Pineco", "hp": 50, "attack": 65, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/204.png"},
{"id": 205, "name": "Forretress", "hp": 75, "attack": 90, "defense": 140, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/205.png"},
{"id": 206, "name": "Dunsparce", "hp": 100, "attack": 70, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/206.png"},
{"id": 207, "name": "Gligar", "hp": 65, "attack": 75, "defense": 105, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/207.png"},
{"id": 208, "name": "Steelix", "hp": 75, "attack": 85, "defense": 200, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/208.png"},
{"id": 209, "name": "Snubbull", "hp": 60, "attack": 80, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/209.png"},
{"id": 210, "name": "Granbull", "hp": 90, "attack": 120, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/210.png"},
{"id": 211, "name": "Qwilfish", "hp": 65, "attack": 95, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/211.png"},
{"id": 212, "name": "Scizor", "hp": 70, "attack": 130, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/212.png"},
{"id": 213, "name": "Shuckle", "hp": 20, "attack": 10, "defense": 230, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/213.png"},
{"id": 214, "name": "Heracross", "hp": 80, "attack": 125, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/214.png"},
{"id": 215, "name": "Sneasel", "hp": 55, "attack": 95, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/215.png"},
{"id": 216, "name": "Teddiursa", "hp": 60, "attack": 80, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/216.png"},
{"id": 217, "name": "Ursaring", "hp": 90, "attack": 130, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/217.png"},
{"id": 218, "name": "Slugma", "hp": 40, "attack": 40, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/218.png"},
{"id": 219, "name": "Magcargo", "hp": 60, "attack": 50, "defense": 120, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/219.png"},
{"id": 220, "name": "Swinub", "hp": 50, "attack": 50, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/220.png"},
{"id": 221, "name": "Piloswine", "hp": 100, "attack": 100, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/221.png"},
{"id": 222, "name": "Corsola", "hp": 65, "attack": 55, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/222.png"},
{"id": 223, "name": "Remoraid", "hp": 35, "attack": 65, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/223.png"},
{"id": 224, "name": "Octillery", "hp": 75, "attack": 105, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/224.png"},
{"id": 225, "name": "Delibird", "hp": 45, "attack": 55, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/225.png"},
{"id": 226, "name": "Mantine", "hp": 85, "attack": 40, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/226.png"},
{"id": 227, "name": "Skarmory", "hp": 65, "attack": 80, "defense": 140, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/227.png"},
{"id": 228, "name": "Houndour", "hp": 45, "attack": 60, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/228.png"},
{"id": 229, "name": "Houndoom", "hp": 75, "attack": 90, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/229.png"},
{"id": 230, "name": "Kingdra", "hp": 75, "attack": 95, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/230.png"},
{"id": 231, "name": "Phanpy", "hp": 90, "attack": 60, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/231.png"},
{"id": 232, "name": "Donphan", "hp": 90, "attack": 120, "defense": 120, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/232.png"},
{"id": 233, "name": "Porygon2", "hp": 85, "attack": 80, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/233.png"},
{"id": 234, "name": "Stantler", "hp": 73, "attack": 95, "defense": 62, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/234.png"},
{"id": 235, "name": "Smeargle", "hp": 55, "attack": 20, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/235.png"},
{"id": 236, "name": "Tyrogue", "hp": 35, "attack": 35, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/236.png"},
{"id": 237, "name": "Hitmontop", "hp": 50, "attack": 95, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/237.png"},
{"id": 238, "name": "Smoochum", "hp": 45, "attack": 30, "defense": 15, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/238.png"},
{"id": 239, "name": "Elekid", "hp": 45, "attack": 63, "defense": 37, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/239.png"},
{"id": 240, "name": "Magby", "hp": 45, "attack": 75, "defense": 37, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/240.png"},
{"id": 241, "name": "Miltank", "hp": 95, "attack": 80, "defense": 105, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/241.png"},
{"id": 242, "name": "Blissey", "hp": 255, "attack": 10, "defense": 10, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/242.png"},
{"id": 243, "name": "Raikou", "hp": 90, "attack": 85, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/243.png"},
{"id": 244, "name": "Entei", "hp": 115, "attack": 115, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/244.png"},
{"id": 245, "name": "Suicune", "hp": 100, "attack": 75, "defense": 115, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/245.png"},
{"id": 246, "name": "Larvitar", "hp": 50, "attack": 64, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/246.png"},
{"id": 247, "name": "Pupitar", "hp": 70, "attack": 84, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/247.png"},
{"id": 248, "name": "Tyranitar", "hp": 100, "attack": 134, "defense": 110, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/248.png"},
{"id": 249, "name": "Lugia", "hp": 106, "attack": 90, "defense": 130, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/249.png"},
{"id": 250, "name": "Ho-Oh", "hp": 106, "attack": 130, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/250.png"},
{"id": 251, "name": "Celebi", "hp": 100, "attack": 100, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/251.png"},
{"id": 252, "name": "Treecko", "hp": 40, "attack": 45, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/252.png"},
{"id": 253, "name": "Grovyle", "hp": 50, "attack": 65, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/253.png"},
{"id": 254, "name": "Sceptile", "hp": 70, "attack": 85, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/254.png"},
{"id": 255, "name": "Torchic", "hp": 45, "attack": 60, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/255.png"},
{"id": 256, "name": "Combusken", "hp": 60, "attack": 85, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/256.png"},
{"id": 257, "name": "Blaziken", "hp": 80, "attack": 120, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/257.png"},
{"id": 258, "name": "Mudkip", "hp": 50, "attack": 70, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/258.png"},
{"id": 259, "name": "Marshtomp", "hp": 70, "attack": 85, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/259.png"},
{"id": 260, "name": "Swampert", "hp": 100, "attack": 110, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/260.png"},
{"id": 261, "name": "Poochyena", "hp": 35, "attack": 55, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/261.png"},
{"id": 262, "name": "Mightyena", "hp": 70, "attack": 90, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/262.png"},
{"id": 263, "name": "Zigzagoon", "hp": 38, "attack": 30, "defense": 41, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/263.png"},
{"id": 264, "name": "Linoone", "hp": 78, "attack": 70, "defense": 61, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/264.png"},
{"id": 265, "name": "Wurmple", "hp": 45, "attack": 45, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/265.png"},
{"id": 266, "name": "Silcoon", "hp": 50, "attack": 35, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/266.png"},
{"id": 267, "name": "Beautifly", "hp": 60, "attack": 70, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/267.png"},
{"id": 268, "name": "Cascoon", "hp": 50, "attack": 35, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/268.png"},
{"id": 269, "name": "Dustox", "hp": 60, "attack": 50, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/269.png"},
{"id": 270, "name": "Lotad", "hp": 40, "attack": 30, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/270.png"},
{"id": 271, "name": "Lombre", "hp": 60, "attack": 50, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/271.png"},
{"id": 272, "name": "Ludicolo", "hp": 80, "attack": 70, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/272.png"},
{"id": 273, "name": "Seedot", "hp": 40, "attack": 40, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/273.png"},
{"id": 274, "name": "Nuzleaf", "hp": 70, "attack": 70, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/274.png"},
{"id": 275, "name": "Shiftry", "hp": 90, "attack": 100, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/275.png"},
{"id": 276, "name": "Taillow", "hp": 40, "attack": 55, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/276.png"},
{"id": 277, "name": "Swellow", "hp": 60, "attack": 85, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/277.png"},
{"id": 278, "name": "Wingull", "hp": 40, "attack": 30, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/278.png"},
{"id": 279, "name": "Pelipper", "hp": 60, "attack": 50, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/279.png"},
{"id": 280, "name": "Ralts", "hp": 28, "attack": 25, "defense": 25, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/280.png"},
{"id": 281, "name": "Kirlia", "hp": 38, "attack": 35, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/281.png"},
{"id": 282, "name": "Gardevoir", "hp": 68, "attack": 65, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/282.png"},
{"id": 283, "name": "Surskit", "hp": 40, "attack": 30, "defense": 32, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/283.png"},
{"id": 284, "name": "Masquerain", "hp": 70, "attack": 60, "defense": 62, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/284.png"},
{"id": 285, "name": "Shroomish", "hp": 60, "attack": 40, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/285.png"},
{"id": 286, "name": "Breloom", "hp": 60, "attack": 130, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/286.png"},
{"id": 287, "name": "Slakoth", "hp": 60, "attack": 60, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/287.png"},
{"id": 288, "name": "Vigoroth", "hp": 80, "attack": 80, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/288.png"},
{"id": 289, "name": "Slaking", "hp": 150, "attack": 160, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/289.png"},
{"id": 290, "name": "Nincada", "hp": 31, "attack": 45, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/290.png"},
{"id": 291, "name": "Ninjask", "hp": 61, "attack": 90, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/291.png"},
{"id": 292, "name": "Shedinja", "hp": 1, "attack": 90, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/292.png"},
{"id": 293, "name": "Whismur", "hp": 64, "attack": 51, "defense": 23, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/293.png"},
{"id": 294, "name": "Loudred", "hp": 84, "attack": 71, "defense": 43, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/294.png"},
{"id": 295, "name": "Exploud", "hp": 104, "attack": 91, "defense": 63, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/295.png"},
{"id": 296, "name": "Makuhita", "hp": 72, "attack": 60, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/296.png"},
{"id": 297, "name": "Hariyama", "hp": 144, "attack": 120, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/297.png"},
{"id": 298, "name": "Azurill", "hp": 50, "attack": 20, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/298.png"},
{"id": 299, "name": "Nosepass", "hp": 30, "attack": 45, "defense": 135, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/299.png"},
{"id": 300, "name": "Skitty", "hp": 50, "attack": 45, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/300.png"}
    ],
4:  [
{"id": 301, "name": "Delcatty", "hp": 70, "attack": 65, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/301.png"},
{"id": 302, "name": "Sableye", "hp": 50, "attack": 75, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/302.png"},
{"id": 303, "name": "Mawile", "hp": 50, "attack": 85, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/303.png"},
{"id": 304, "name": "Aron", "hp": 50, "attack": 70, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/304.png"},
{"id": 305, "name": "Lairon", "hp": 60, "attack": 90, "defense": 140, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/305.png"},
{"id": 306, "name": "Aggron", "hp": 70, "attack": 110, "defense": 180, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/306.png"},
{"id": 307, "name": "Meditite", "hp": 30, "attack": 40, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/307.png"},
{"id": 308, "name": "Medicham", "hp": 60, "attack": 60, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/308.png"},
{"id": 309, "name": "Electrike", "hp": 40, "attack": 45, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/309.png"},
{"id": 310, "name": "Manectric", "hp": 70, "attack": 75, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/310.png"},
{"id": 311, "name": "Plusle", "hp": 60, "attack": 50, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/311.png"},
{"id": 312, "name": "Minun", "hp": 60, "attack": 40, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/312.png"},
{"id": 313, "name": "Volbeat", "hp": 65, "attack": 73, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/313.png"},
{"id": 314, "name": "Illumise", "hp": 65, "attack": 47, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/314.png"},
{"id": 315, "name": "Roselia", "hp": 50, "attack": 60, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/315.png"},
{"id": 316, "name": "Gulpin", "hp": 70, "attack": 43, "defense": 53, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/316.png"},
{"id": 317, "name": "Swalot", "hp": 100, "attack": 73, "defense": 83, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/317.png"},
{"id": 318, "name": "Carvanha", "hp": 45, "attack": 90, "defense": 20, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/318.png"},
{"id": 319, "name": "Sharpedo", "hp": 70, "attack": 120, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/319.png"},
{"id": 320, "name": "Wailmer", "hp": 130, "attack": 70, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/320.png"},
{"id": 321, "name": "Wailord", "hp": 170, "attack": 90, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/321.png"},
{"id": 322, "name": "Numel", "hp": 60, "attack": 60, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/322.png"},
{"id": 323, "name": "Camerupt", "hp": 70, "attack": 100, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/323.png"},
{"id": 324, "name": "Torkoal", "hp": 70, "attack": 85, "defense": 140, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/324.png"},
{"id": 325, "name": "Spoink", "hp": 60, "attack": 25, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/325.png"},
{"id": 326, "name": "Grumpig", "hp": 80, "attack": 45, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/326.png"},
{"id": 327, "name": "Spinda", "hp": 60, "attack": 60, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/327.png"},
{"id": 328, "name": "Trapinch", "hp": 45, "attack": 100, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/328.png"},
{"id": 329, "name": "Vibrava", "hp": 50, "attack": 70, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/329.png"},
{"id": 330, "name": "Flygon", "hp": 80, "attack": 100, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/330.png"},
{"id": 331, "name": "Cacnea", "hp": 50, "attack": 85, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/331.png"},
{"id": 332, "name": "Cacturne", "hp": 70, "attack": 115, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/332.png"},
{"id": 333, "name": "Swablu", "hp": 45, "attack": 40, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/333.png"},
{"id": 334, "name": "Altaria", "hp": 75, "attack": 70, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/334.png"},
{"id": 335, "name": "Zangoose", "hp": 73, "attack": 115, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/335.png"},
{"id": 336, "name": "Seviper", "hp": 73, "attack": 100, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/336.png"},
{"id": 337, "name": "Lunatone", "hp": 90, "attack": 55, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/337.png"},
{"id": 338, "name": "Solrock", "hp": 90, "attack": 95, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/338.png"},
{"id": 339, "name": "Barboach", "hp": 50, "attack": 48, "defense": 43, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/339.png"},
{"id": 340, "name": "Whiscash", "hp": 110, "attack": 78, "defense": 73, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/340.png"},
{"id": 341, "name": "Corphish", "hp": 43, "attack": 80, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/341.png"},
{"id": 342, "name": "Crawdaunt", "hp": 63, "attack": 120, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/342.png"},
{"id": 343, "name": "Baltoy", "hp": 40, "attack": 40, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/343.png"},
{"id": 344, "name": "Claydol", "hp": 60, "attack": 70, "defense": 105, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/344.png"},
{"id": 345, "name": "Lileep", "hp": 66, "attack": 41, "defense": 77, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/345.png"},
{"id": 346, "name": "Cradily", "hp": 86, "attack": 81, "defense": 97, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/346.png"},
{"id": 347, "name": "Anorith", "hp": 45, "attack": 95, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/347.png"},
{"id": 348, "name": "Armaldo", "hp": 75, "attack": 125, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/348.png"},
{"id": 349, "name": "Feebas", "hp": 20, "attack": 15, "defense": 20, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/349.png"},
{"id": 350, "name": "Milotic", "hp": 95, "attack": 60, "defense": 79, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/350.png"},
{"id": 351, "name": "Castform", "hp": 70, "attack": 70, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/351.png"},
{"id": 352, "name": "Kecleon", "hp": 60, "attack": 90, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/352.png"},
{"id": 353, "name": "Shuppet", "hp": 44, "attack": 75, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/353.png"},
{"id": 354, "name": "Banette", "hp": 64, "attack": 115, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/354.png"},
{"id": 355, "name": "Duskull", "hp": 20, "attack": 40, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/355.png"},
{"id": 356, "name": "Dusclops", "hp": 40, "attack": 70, "defense": 130, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/356.png"},
{"id": 357, "name": "Tropius", "hp": 99, "attack": 68, "defense": 83, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/357.png"},
{"id": 358, "name": "Chimecho", "hp": 75, "attack": 50, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/358.png"},
{"id": 359, "name": "Absol", "hp": 65, "attack": 130, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/359.png"},
{"id": 360, "name": "Wynaut", "hp": 95, "attack": 23, "defense": 48, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/360.png"},
{"id": 361, "name": "Snorunt", "hp": 50, "attack": 50, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/361.png"},
{"id": 362, "name": "Glalie", "hp": 80, "attack": 80, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/362.png"},
{"id": 363, "name": "Spheal", "hp": 70, "attack": 40, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/363.png"},
{"id": 364, "name": "Sealeo", "hp": 90, "attack": 60, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/364.png"},
{"id": 365, "name": "Walrein", "hp": 110, "attack": 80, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/365.png"},
{"id": 366, "name": "Clamperl", "hp": 35, "attack": 64, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/366.png"},
{"id": 367, "name": "Huntail", "hp": 55, "attack": 104, "defense": 105, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/367.png"},
{"id": 368, "name": "Gorebyss", "hp": 55, "attack": 84, "defense": 105, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/368.png"},
{"id": 369, "name": "Relicanth", "hp": 100, "attack": 90, "defense": 130, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/369.png"},
{"id": 370, "name": "Luvdisc", "hp": 43, "attack": 30, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/370.png"},
{"id": 371, "name": "Bagon", "hp": 45, "attack": 75, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/371.png"},
{"id": 372, "name": "Shelgon", "hp": 65, "attack": 95, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/372.png"},
{"id": 373, "name": "Salamence", "hp": 95, "attack": 135, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/373.png"},
{"id": 374, "name": "Beldum", "hp": 40, "attack": 55, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/374.png"},
{"id": 375, "name": "Metang", "hp": 60, "attack": 75, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/375.png"},
{"id": 376, "name": "Metagross", "hp": 80, "attack": 135, "defense": 130, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/376.png"},
{"id": 377, "name": "Regirock", "hp": 80, "attack": 100, "defense": 200, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/377.png"},
{"id": 378, "name": "Regice", "hp": 80, "attack": 50, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/378.png"},
{"id": 379, "name": "Registeel", "hp": 80, "attack": 75, "defense": 150, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/379.png"},
{"id": 380, "name": "Latias", "hp": 80, "attack": 80, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/380.png"},
{"id": 381, "name": "Latios", "hp": 80, "attack": 90, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/381.png"},
{"id": 382, "name": "Kyogre", "hp": 100, "attack": 100, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/382.png"},
{"id": 383, "name": "Groudon", "hp": 100, "attack": 150, "defense": 140, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/383.png"},
{"id": 384, "name": "Rayquaza", "hp": 105, "attack": 150, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/384.png"},
{"id": 385, "name": "Jirachi", "hp": 100, "attack": 100, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/385.png"},
{"id": 386, "name": "Deoxys", "hp": 50, "attack": 150, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/386.png"},
{"id": 387, "name": "Turtwig", "hp": 55, "attack": 68, "defense": 64, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/387.png"},
{"id": 388, "name": "Grotle", "hp": 75, "attack": 89, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/388.png"},
{"id": 389, "name": "Torterra", "hp": 95, "attack": 109, "defense": 105, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/389.png"},
{"id": 390, "name": "Chimchar", "hp": 44, "attack": 58, "defense": 44, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/390.png"},
{"id": 391, "name": "Monferno", "hp": 64, "attack": 78, "defense": 52, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/391.png"},
{"id": 392, "name": "Infernape", "hp": 76, "attack": 104, "defense": 71, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/392.png"},
{"id": 393, "name": "Piplup", "hp": 53, "attack": 51, "defense": 53, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/393.png"},
{"id": 394, "name": "Prinplup", "hp": 64, "attack": 66, "defense": 68, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/394.png"},
{"id": 395, "name": "Empoleon", "hp": 84, "attack": 86, "defense": 88, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/395.png"},
{"id": 396, "name": "Starly", "hp": 40, "attack": 55, "defense": 30, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/396.png"},
{"id": 397, "name": "Staravia", "hp": 55, "attack": 75, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/397.png"},
{"id": 398, "name": "Staraptor", "hp": 85, "attack": 120, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/398.png"},
{"id": 399, "name": "Bidoof", "hp": 59, "attack": 45, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/399.png"},
{"id": 400, "name": "Bibarel", "hp": 79, "attack": 85, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/400.png"},
    ],
5:     [
    {"id": 401, "name": "Kricketot", "hp": 37, "attack": 25, "defense": 41, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/401.png"},
    {"id": 402, "name": "Kricketune", "hp": 77, "attack": 85, "defense": 51, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/402.png"},
    {"id": 403, "name": "Shinx", "hp": 45, "attack": 65, "defense": 34, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/403.png"},
    {"id": 404, "name": "Luxio", "hp": 60, "attack": 85, "defense": 49, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/404.png"},
    {"id": 405, "name": "Luxray", "hp": 80, "attack": 120, "defense": 79, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/405.png"},
    {"id": 406, "name": "Budew", "hp": 40, "attack": 30, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/406.png"},
    {"id": 407, "name": "Roserade", "hp": 60, "attack": 70, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/407.png"},
    {"id": 408, "name": "Cranidos", "hp": 67, "attack": 125, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/408.png"},
    {"id": 409, "name": "Rampardos", "hp": 97, "attack": 165, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/409.png"},
    {"id": 410, "name": "Shieldon", "hp": 30, "attack": 42, "defense": 118, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/410.png"},
    {"id": 411, "name": "Bastiodon", "hp": 60, "attack": 52, "defense": 168, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/411.png"},
    {"id": 412, "name": "Burmy", "hp": 40, "attack": 29, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/412.png"},
    {"id": 413, "name": "Wormadam", "hp": 60, "attack": 59, "defense": 85, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/413.png"},
    {"id": 414, "name": "Mothim", "hp": 70, "attack": 94, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/414.png"},
    {"id": 415, "name": "Combee", "hp": 30, "attack": 30, "defense": 42, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/415.png"},
    {"id": 416, "name": "Vespiquen", "hp": 70, "attack": 80, "defense": 102, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/416.png"},
    {"id": 417, "name": "Pachirisu", "hp": 60, "attack": 45, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/417.png"},
    {"id": 418, "name": "Buizel", "hp": 55, "attack": 65, "defense": 35, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/418.png"},
    {"id": 419, "name": "Floatzel", "hp": 85, "attack": 105, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/419.png"},
    {"id": 420, "name": "Cherubi", "hp": 45, "attack": 35, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/420.png"},
    {"id": 421, "name": "Cherrim", "hp": 70, "attack": 60, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/421.png"},
    {"id": 422, "name": "Shellos", "hp": 76, "attack": 48, "defense": 48, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/422.png"},
    {"id": 423, "name": "Gastrodon", "hp": 111, "attack": 83, "defense": 68, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/423.png"},
    {"id": 424, "name": "Ambipom", "hp": 75, "attack": 100, "defense": 66, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/424.png"},
    {"id": 425, "name": "Drifloon", "hp": 90, "attack": 50, "defense": 34, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/425.png"},
    {"id": 426, "name": "Drifblim", "hp": 150, "attack": 80, "defense": 44, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/426.png"},
    {"id": 427, "name": "Buneary", "hp": 55, "attack": 66, "defense": 44, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/427.png"},
    {"id": 428, "name": "Lopunny", "hp": 65, "attack": 76, "defense": 84, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/428.png"},
    {"id": 429, "name": "Mismagius", "hp": 60, "attack": 60, "defense": 60, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/429.png"},
    {"id": 430, "name": "Honchkrow", "hp": 100, "attack": 125, "defense": 52, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/430.png"},
    {"id": 431, "name": "Glameow", "hp": 49, "attack": 55, "defense": 42, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/431.png"},
    {"id": 432, "name": "Purugly", "hp": 71, "attack": 82, "defense": 64, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/432.png"},
    {"id": 433, "name": "Chingling", "hp": 45, "attack": 30, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/433.png"},
    {"id": 434, "name": "Stunky", "hp": 63, "attack": 63, "defense": 47, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/434.png"},
    {"id": 435, "name": "Skuntank", "hp": 103, "attack": 93, "defense": 67, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/435.png"},
    {"id": 436, "name": "Bronzor", "hp": 57, "attack": 24, "defense": 86, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/436.png"},
    {"id": 437, "name": "Bronzong", "hp": 67, "attack": 89, "defense": 116, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/437.png"},
    {"id": 438, "name": "Bonsly", "hp": 50, "attack": 80, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/438.png"},
    {"id": 439, "name": "Mime Jr.", "hp": 20, "attack": 25, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/439.png"},
    {"id": 440, "name": "Happiny", "hp": 100, "attack": 5, "defense": 5, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/440.png"},
    {"id": 441, "name": "Chatot", "hp": 76, "attack": 65, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/441.png"},
    {"id": 442, "name": "Spiritomb", "hp": 50, "attack": 92, "defense": 108, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/442.png"},
    {"id": 443, "name": "Gible", "hp": 58, "attack": 70, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/443.png"},
    {"id": 444, "name": "Gabite", "hp": 68, "attack": 90, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/444.png"},
    {"id": 445, "name": "Garchomp", "hp": 108, "attack": 130, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/445.png"},
    {"id": 446, "name": "Munchlax", "hp": 135, "attack": 85, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/446.png"},
    {"id": 447, "name": "Riolu", "hp": 40, "attack": 70, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/447.png"},
    {"id": 448, "name": "Lucario", "hp": 70, "attack": 110, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/448.png"},
    {"id": 449, "name": "Hippopotas", "hp": 68, "attack": 72, "defense": 78, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/449.png"},
    {"id": 450, "name": "Hippowdon", "hp": 108, "attack": 112, "defense": 118, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/450.png"},
    {"id": 451, "name": "Skorupi", "hp": 40, "attack": 50, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/451.png"},
    {"id": 452, "name": "Drapion", "hp": 70, "attack": 90, "defense": 110, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/452.png"},
    {"id": 453, "name": "Croagunk", "hp": 48, "attack": 61, "defense": 40, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/453.png"},
    {"id": 454, "name": "Toxicroak", "hp": 83, "attack": 106, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/454.png"},
    {"id": 455, "name": "Carnivine", "hp": 74, "attack": 100, "defense": 72, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/455.png"},
    {"id": 456, "name": "Finneon", "hp": 49, "attack": 49, "defense": 56, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/456.png"},
    {"id": 457, "name": "Lumineon", "hp": 69, "attack": 69, "defense": 76, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/457.png"},
    {"id": 458, "name": "Mantyke", "hp": 45, "attack": 20, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/458.png"},
    {"id": 459, "name": "Snover", "hp": 60, "attack": 62, "defense": 50, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/459.png"},
    {"id": 460, "name": "Abomasnow", "hp": 90, "attack": 92, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/460.png"},
    {"id": 461, "name": "Weavile", "hp": 70, "attack": 120, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/461.png"},
    {"id": 462, "name": "Magnezone", "hp": 70, "attack": 70, "defense": 115, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/462.png"},
    {"id": 463, "name": "Lickilicky", "hp": 110, "attack": 85, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/463.png"},
    {"id": 464, "name": "Rhyperior", "hp": 115, "attack": 140, "defense": 130, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/464.png"},
    {"id": 465, "name": "Tangrowth", "hp": 100, "attack": 100, "defense": 125, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/465.png"},
    {"id": 466, "name": "Electivire", "hp": 75, "attack": 123, "defense": 67, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/466.png"},
    {"id": 467, "name": "Magmortar", "hp": 75, "attack": 95, "defense": 67, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/467.png"},
    {"id": 468, "name": "Togekiss", "hp": 85, "attack": 50, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/468.png"},
    {"id": 469, "name": "Yanmega", "hp": 86, "attack": 76, "defense": 86, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/469.png"},
    {"id": 470, "name": "Leafeon", "hp": 65, "attack": 110, "defense": 130, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/470.png"},
    {"id": 471, "name": "Glaceon", "hp": 65, "attack": 60, "defense": 110, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/471.png"},
    {"id": 472, "name": "Gliscor", "hp": 75, "attack": 95, "defense": 125, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/472.png"},
    {"id": 473, "name": "Mamoswine", "hp": 110, "attack": 130, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/473.png"},
    {"id": 474, "name": "Porygon-Z", "hp": 85, "attack": 80, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/474.png"},
    {"id": 475, "name": "Gallade", "hp": 68, "attack": 125, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/475.png"},
    {"id": 476, "name": "Probopass", "hp": 60, "attack": 55, "defense": 145, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/476.png"},
    {"id": 477, "name": "Dusknoir", "hp": 45, "attack": 100, "defense": 135, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/477.png"},
    {"id": 478, "name": "Froslass", "hp": 70, "attack": 80, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/478.png"},
    {"id": 479, "name": "Rotom", "hp": 50, "attack": 50, "defense": 77, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/479.png"},
    {"id": 480, "name": "Uxie", "hp": 75, "attack": 75, "defense": 130, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/480.png"},
    {"id": 481, "name": "Mesprit", "hp": 80, "attack": 105, "defense": 105, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/481.png"},
    {"id": 482, "name": "Azelf", "hp": 75, "attack": 125, "defense": 70, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/482.png"},
    {"id": 483, "name": "Dialga", "hp": 100, "attack": 120, "defense": 120, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/483.png"},
    {"id": 484, "name": "Palkia", "hp": 90, "attack": 120, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/484.png"},
    {"id": 485, "name": "Heatran", "hp": 91, "attack": 90, "defense": 106, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/485.png"},
    {"id": 486, "name": "Regigigas", "hp": 110, "attack": 160, "defense": 110, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/486.png"},
    {"id": 487, "name": "Giratina", "hp": 150, "attack": 100, "defense": 120, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/487.png"},
    {"id": 488, "name": "Cresselia", "hp": 120, "attack": 70, "defense": 120, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/488.png"},
    {"id": 489, "name": "Phione", "hp": 80, "attack": 80, "defense": 80, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/489.png"},
    {"id": 490, "name": "Manaphy", "hp": 100, "attack": 100, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/490.png"},
    {"id": 491, "name": "Darkrai", "hp": 70, "attack": 90, "defense": 90, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/491.png"},
    {"id": 492, "name": "Shaymin", "hp": 100, "attack": 100, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/492.png"},
    {"id": 493, "name": "Arceus", "hp": 120, "attack": 120, "defense": 120, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/493.png"},
    {"id": 494, "name": "Victini", "hp": 100, "attack": 100, "defense": 100, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/494.png"},
    {"id": 495, "name": "Snivy", "hp": 45, "attack": 45, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/495.png"},
    {"id": 496, "name": "Servine", "hp": 60, "attack": 60, "defense": 75, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/496.png"},
    {"id": 497, "name": "Serperior", "hp": 75, "attack": 75, "defense": 95, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/497.png"},
    {"id": 498, "name": "Tepig", "hp": 65, "attack": 63, "defense": 45, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/498.png"},
    {"id": 499, "name": "Pignite", "hp": 90, "attack": 93, "defense": 55, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/499.png"},
    {"id": 500, "name": "Emboar", "hp": 110, "attack": 123, "defense": 65, "image": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/500.png"}
    ]

}

# Состояния для FSM
class CreatePokemonState(StatesGroup):
    name = State()
    image = State()
    hp = State()
    attack = State()
    defense = State()

class ChangeBalanceState(StatesGroup):
    user_id = State()
    amount = State()

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, is_admin) VALUES (?, ?, ?)", 
                  (user_id, username, user_id in ADMIN_IDS))
    conn.commit()
    
    await message.answer(
        f"🐲 Добро пожаловать в мир Покемонов, {username}!",
        reply_markup=get_main_menu(user_id)
    )

@dp.message(F.text == "🔙 Назад")
@dp.message(F.text == "Назад")
async def back_handler(message: Message):
    await message.answer("Главное меню:", reply_markup=get_main_menu(message.from_user.id))

# ========== АДМИН-ПАНЕЛЬ ==========

@dp.message(F.text == "👑 Админ-панель")
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer("👑 Админ-панель:", reply_markup=get_admin_menu())

@dp.message(F.text == "Изменить баланс")
async def change_balance_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer("Введите ID пользователя:")
    await state.set_state(ChangeBalanceState.user_id)

@dp.message(ChangeBalanceState.user_id)
async def process_user_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        await state.update_data(user_id=user_id)
        await message.answer("Введите сумму для изменения баланса (можно отрицательную):")
        await state.set_state(ChangeBalanceState.amount)
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя!")

@dp.message(ChangeBalanceState.amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        data = await state.get_data()
        user_id = data['user_id']
        
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        
        if cursor.rowcount == 0:
            await message.answer("❌ Пользователь не найден!")
        else:
            await message.answer(f"✅ Баланс пользователя {user_id} изменен на {amount} монет")
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Некорректная сумма!")

# ========== ЛОВЛЯ ПОКЕМОНОВ ==========

@dp.message(F.text == "🎣 Ловить покемона")
async def catch_pokemon(message: Message):
    user_id = message.from_user.id
    
    # Проверяем есть ли покебалы
    cursor.execute("SELECT pokeballs FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if not result or result[0] <= 0:
        await message.answer("❌ У вас закончились покебалы! Купите их в магазине.")
        return
    
    # Определяем лигу пользователя
    cursor.execute("SELECT trainer_level FROM users WHERE user_id = ?", (user_id,))
    league = min(cursor.fetchone()[0], len(POKEMONS))
    
    # Генерируем покемона
    pokemon = random.choice(POKEMONS[league])
    
    # Уменьшаем количество покеболов
    cursor.execute("UPDATE users SET pokeballs = pokeballs - 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    
    # Добавляем в покедекс
    cursor.execute("INSERT OR IGNORE INTO pokedex (user_id, pokemon_id) VALUES (?, ?)", (user_id, pokemon['id']))
    cursor.execute("UPDATE pokedex SET seen = TRUE WHERE user_id = ? AND pokemon_id = ?", (user_id, pokemon['id']))
    conn.commit()
    
    # Клавиатура для ловли
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Поймать!", callback_data=f"catch_{pokemon['id']}")],
        [InlineKeyboardButton(text="Убежать", callback_data="run_away")]
    ])
    
    await message.answer_photo(
        photo=pokemon['image'],
        caption=f"Вы встретили дикого {pokemon['name']}!\nHP: {pokemon['hp']} | ATK: {pokemon['attack']} | DEF: {pokemon['defense']}",
        reply_markup=keyboard
    )

@dp.callback_query(F.data.startswith("catch_"))
async def catch_pokemon_callback(callback: CallbackQuery):
    pokemon_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    # Находим покемона
    pokemon = None
    for league in POKEMONS.values():
        for p in league:
            if p['id'] == pokemon_id:
                pokemon = p
                break
        if pokemon:
            break
    
    if not pokemon:
        await callback.answer("❌ Ошибка: покемон не найден")
        return
    
    # Проверяем лимит (максимум 3 одинаковых покемона)
    cursor.execute("SELECT count FROM pokemon_counts WHERE user_id = ? AND pokemon_id = ?", (user_id, pokemon_id))
    result = cursor.fetchone()
    if result and result[0] >= 3:
        await callback.message.edit_caption(
            caption=f"❌ У вас уже есть 3 {pokemon['name']}! Максимальное количество достигнуто.",
            reply_markup=None
        )
        await callback.answer()
        return
    
    # Шанс поймать зависит от HP покемона
    catch_chance = min(90, max(10, 100 - pokemon['hp']))
    
    if random.randint(1, 100) <= catch_chance:
        # Добавляем покемона
        cursor.execute("""
            INSERT INTO pokemons (owner_id, pokemon_id, name, image, hp, attack, defense)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, pokemon['id'], pokemon['name'], pokemon['image'], pokemon['hp'], pokemon['attack'], pokemon['defense']))
        
        # Обновляем счетчик
        cursor.execute("""
            INSERT OR IGNORE INTO pokemon_counts (user_id, pokemon_id, count) 
            VALUES (?, ?, 0)
        """, (user_id, pokemon['id']))
        
        cursor.execute("""
            UPDATE pokemon_counts SET count = count + 1 
            WHERE user_id = ? AND pokemon_id = ?
        """, (user_id, pokemon['id']))
        
        # Обновляем общую статистику
        cursor.execute("UPDATE users SET total_pokemons = total_pokemons + 1 WHERE user_id = ?", (user_id,))
        
        # Помечаем как пойманного
        cursor.execute("UPDATE pokedex SET caught = TRUE WHERE user_id = ? AND pokemon_id = ?", (user_id, pokemon['id']))
        
        conn.commit()
        
        await callback.message.edit_caption(
            caption=f"🎉 Вы поймали {pokemon['name']}!",
            reply_markup=None
        )
    else:
        await callback.message.edit_caption(
            caption=f"❌ {pokemon['name']} сбежал! Попробуйте еще раз.",
            reply_markup=None
        )
    
    await callback.answer()

@dp.callback_query(F.data == "run_away")
async def run_away_callback(callback: CallbackQuery):
    await callback.message.edit_caption(
        caption="Вы убежали от покемона!",
        reply_markup=None
    )
    await callback.answer()

# ========== МАГАЗИН ==========

@dp.message(F.text == "🛒 Магазин")
async def shop_handler(message: Message):
    await message.answer("🛒 Добро пожаловать в магазин!", reply_markup=get_shop_menu())

@dp.message(F.text == "🎣 Купить покебал (500)")
async def buy_pokeball(message: Message):
    user_id = message.from_user.id
    cursor.execute("UPDATE users SET balance = balance - 500, pokeballs = pokeballs + 1 WHERE user_id = ? AND balance >= 500", (user_id,))
    
    if cursor.rowcount == 0:
        await message.answer("❌ Недостаточно монет!")
    else:
        conn.commit()
        await message.answer("🎣 Вы купили 1 покебал!")
    
    await message.answer("🛒 Магазин:", reply_markup=get_shop_menu())

@dp.message(F.text == "👨‍🏫 Нанять тренера")
async def hire_trainer_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    cursor.execute("SELECT * FROM trainers")
    trainers = cursor.fetchall()
    
    for trainer in trainers:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{trainer[1]} - {trainer[2]} монет (+{trainer[3]}/час)",
                callback_data=f"hire_{trainer[0]}"
            )
        ])
    
    await message.answer("Выберите тренера:", reply_markup=keyboard)

@dp.callback_query(F.data.startswith("hire_"))
async def hire_trainer(callback: CallbackQuery):
    trainer_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    cursor.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,))
    trainer = cursor.fetchone()
    
    if not trainer:
        await callback.answer("❌ Тренер не найден!")
        return
    
    cursor.execute("""
        UPDATE users 
        SET balance = balance - ?, trainer_id = ?, trainer_level = trainer_level + 1 
        WHERE user_id = ? AND balance >= ?
    """, (trainer[2], trainer_id, user_id, trainer[2]))
    
    if cursor.rowcount == 0:
        await callback.answer("❌ Недостаточно монет!")
    else:
        conn.commit()
        await callback.message.answer(f"👨‍🏫 Вы наняли тренера {trainer[1]}! Ваш уровень тренера увеличен.")
    
    await callback.answer()

# ========== СТАТИСТИКА ==========

@dp.message(F.text == "📊 Моя статистика")
async def stats_handler(message: Message):
    user_id = message.from_user.id
    
    cursor.execute("""
        SELECT username, balance, pokeballs, total_pokemons, trainer_level
        FROM users WHERE user_id = ?
    """, (user_id,))
    data = cursor.fetchone()
    
    if not data:
        await message.answer("❌ Произошла ошибка!")
        return
    
    username, balance, pokeballs, total_pokemons, trainer_level = data
    
    # Получаем информацию о тренере
    trainer_info = ""
    cursor.execute("""
        SELECT t.name, t.income FROM users u
        JOIN trainers t ON u.trainer_id = t.id
        WHERE u.user_id = ?
    """, (user_id,))
    trainer = cursor.fetchone()
    
    if trainer:
        trainer_name, trainer_income = trainer
        trainer_info = f"\n👨‍🏫 Тренер: {trainer_name} (+{trainer_income} монет/час)"
    
    # Получаем количество уникальных покемонов
    cursor.execute("SELECT COUNT(DISTINCT pokemon_id) FROM pokemons WHERE owner_id = ?", (user_id,))
    unique_pokemons = cursor.fetchone()[0]
    
    await message.answer(
        f"📊 Ваша статистика:\n"
        f"👤 Имя: {username}\n"
        f"💰 Монеты: {balance}\n"
        f"🎣 Покебалы: {pokeballs}\n"
        f"🐲 Всего покемонов: {total_pokemons}\n"
        f"🔄 Уникальных покемонов: {unique_pokemons}\n"
        f"🏅 Уровень тренера: {trainer_level}"
        f"{trainer_info}"
    )

# ========== МОИ ПОКЕМОНЫ ==========

@dp.message(F.text == "📦 Мои покемоны")
async def my_pokemons_handler(message: Message):
    user_id = message.from_user.id
    
    cursor.execute("""
        SELECT p.pokemon_id, p.name, p.image, pc.count 
        FROM pokemon_counts pc
        JOIN (SELECT DISTINCT pokemon_id, name, image FROM pokemons WHERE owner_id = ?) p
        ON pc.pokemon_id = p.pokemon_id
        WHERE pc.user_id = ?
        ORDER BY pc.count DESC, p.name
    """, (user_id, user_id))
    pokemons = cursor.fetchall()
    
    if not pokemons:
        await message.answer("❌ У вас пока нет покемонов!")
        return
    
    response = "📦 Ваши покемоны:\n\n"
    for pokemon in pokemons:
        pokemon_id, name, image, count = pokemon
        response += f"{name} ×{count}\n"
    
    await message.answer(response)

# ========== ПОКЕДЕКС ==========

@dp.message(F.text == "📘 Покедекс")
async def pokedex_handler(message: Message):
    user_id = message.from_user.id
    current_league = min(cursor.execute("SELECT trainer_level FROM users WHERE user_id = ?", (user_id,)).fetchone()[0], len(POKEMONS))
    
    cursor.execute("SELECT COUNT(*) FROM pokedex WHERE user_id = ? AND caught = TRUE", (user_id,))
    caught = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM pokedex WHERE user_id = ? AND seen = TRUE", (user_id,))
    seen = cursor.fetchone()[0]
    
    # Считаем общее количество покемонов в доступных лигах
    total_in_leagues = sum(len(POKEMONS.get(league, [])) for league in range(1, current_league + 1))
    
    await message.answer(
        f"📘 Ваш Покедекс:\n"
        f"✅ Поймано: {caught}\n"
        f"👀 Видели: {seen}\n"
        f"🏆 Доступно покемонов: {total_in_leagues}\n"
        f"🔍 Прогресс: {round(caught/total_in_leagues*100, 1) if total_in_leagues > 0 else 0}%"
    )

# ========== СОЗДАНИЕ ПОКЕМОНОВ (АДМИН) ==========

@dp.message(F.text == "Создать покемона")
async def create_pokemon_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer("Введите имя покемона:")
    await state.set_state(CreatePokemonState.name)

@dp.message(CreatePokemonState.name)
async def create_pokemon_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите URL изображения покемона:")
    await state.set_state(CreatePokemonState.image)

@dp.message(CreatePokemonState.image)
async def create_pokemon_image(message: Message, state: FSMContext):
    await state.update_data(image=message.text)
    await message.answer("Введите HP покемона:")
    await state.set_state(CreatePokemonState.hp)

@dp.message(CreatePokemonState.hp)
async def create_pokemon_hp(message: Message, state: FSMContext):
    try:
        hp = int(message.text)
        await state.update_data(hp=hp)
        await message.answer("Введите атаку покемона:")
        await state.set_state(CreatePokemonState.attack)
    except ValueError:
        await message.answer("❌ Введите число!")

@dp.message(CreatePokemonState.attack)
async def create_pokemon_attack(message: Message, state: FSMContext):
    try:
        attack = int(message.text)
        await state.update_data(attack=attack)
        await message.answer("Введите защиту покемона:")
        await state.set_state(CreatePokemonState.defense)
    except ValueError:
        await message.answer("❌ Введите число!")

@dp.message(CreatePokemonState.defense)
async def create_pokemon_defense(message: Message, state: FSMContext):
    try:
        defense = int(message.text)
        data = await state.get_data()
        
        cursor.execute("""
            INSERT INTO custom_pokemons (name, image, hp, attack, defense)
            VALUES (?, ?, ?, ?, ?)
        """, (data['name'], data['image'], data['hp'], data['attack'], defense))
        conn.commit()
        
        await message.answer(f"✅ Покемон {data['name']} успешно создан!")
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число!")
    except sqlite3.IntegrityError:
        await message.answer("❌ Покемон с таким именем уже существует!")
        await state.clear()

# ========== ЗАПУСК ==========

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())