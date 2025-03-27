import os
import random
import sqlite3
import asyncio
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from keep_alive import keep_alive

# Загрузка данных о покемонах из внешнего файла
with open('pokemons.json', 'r') as f:
    POKEMONS = json.load(f)

TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_IDS = [5953677116]
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

# База данных
conn = sqlite3.connect('pokemon.db', check_same_thread=False)
cursor = conn.cursor()

# Инициализация БД
cursor.executescript('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 3000,
    pokeballs INTEGER DEFAULT 5,
    total_pokemons INTEGER DEFAULT 0,
    is_admin BOOLEAN DEFAULT FALSE,
    trainer_id INTEGER DEFAULT NULL,
    trainer_level INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS pokemons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER,
    pokemon_id INTEGER,
    name TEXT,
    image TEXT,
    hp INTEGER,
    attack INTEGER,
    defense INTEGER,
    is_custom BOOLEAN DEFAULT FALSE,
    FOREIGN KEY(owner_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS pokemon_counts (
    user_id INTEGER,
    pokemon_id INTEGER,
    count INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, pokemon_id)
);

CREATE TABLE IF NOT EXISTS custom_pokemons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    image TEXT,
    hp INTEGER,
    attack INTEGER,
    defense INTEGER
);

CREATE TABLE IF NOT EXISTS trainers (
    id INTEGER PRIMARY KEY,
    name TEXT,
    price INTEGER,
    income INTEGER,
    image TEXT
);

CREATE TABLE IF NOT EXISTS pokedex (
    user_id INTEGER,
    pokemon_id INTEGER,
    seen BOOLEAN DEFAULT FALSE,
    caught BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (user_id, pokemon_id)
);
''')

# Заполняем тренеров
if not cursor.execute("SELECT COUNT(*) FROM trainers").fetchone()[0]:
    cursor.executemany(
        "INSERT INTO trainers VALUES (?, ?, ?, ?, ?)",
        [
            (1, "Брок", 10000, 100, "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/trainer/1.png"),
            (2, "Мсти", 25000, 250, "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/trainer/2.png"),
            (3, "Эш", 50000, 500, "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/trainer/3.png")
        ]
    )
    conn.commit()

# Меню
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

def get_admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать покемона")],
            [KeyboardButton(text="Изменить баланс")],
            [KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True
    )

def get_shop_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎣 Купить покебал (500)")],
            [KeyboardButton(text="👨‍🏫 Нанять тренера")],
            [KeyboardButton(text="🔙 Назад")]
        ],
        resize_keyboard=True
    )

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
    
    await message.answer(f"🐲 Добро пожаловать в мир Покемонов, {username}!", reply_markup=get_main_menu(user_id))

@dp.message(F.text == "🔙 Назад")
@dp.message(F.text == "Назад")
async def back_handler(message: Message):
    await message.answer("Главное меню:", reply_markup=get_main_menu(message.from_user.id))

# ========== АДМИН-ПАНЕЛЬ ==========
@dp.message(F.text == "👑 Админ-панель")
async def admin_panel(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("👑 Админ-панель:", reply_markup=get_admin_menu())

@dp.message(F.text == "Изменить баланс")
async def change_balance_start(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Введите ID пользователя:")
        await state.set_state(ChangeBalanceState.user_id)

@dp.message(ChangeBalanceState.user_id)
async def process_user_id(message: Message, state: FSMContext):
    try:
        await state.update_data(user_id=int(message.text))
        await message.answer("Введите сумму для изменения баланса (можно отрицательную):")
        await state.set_state(ChangeBalanceState.amount)
    except ValueError:
        await message.answer("❌ Некорректный ID пользователя!")

@dp.message(ChangeBalanceState.amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", 
                       (int(message.text), data['user_id']))
        conn.commit()
        
        if cursor.rowcount:
            await message.answer(f"✅ Баланс пользователя {data['user_id']} изменен на {message.text} монет")
        else:
            await message.answer("❌ Пользователь не найден!")
    except ValueError:
        await message.answer("❌ Некорректная сумма!")
    await state.clear()

# ========== ЛОВЛЯ ПОКЕМОНОВ ==========
@dp.message(F.text == "🎣 Ловить покемона")
async def catch_pokemon(message: Message):
    user_id = message.from_user.id
    if cursor.execute("SELECT pokeballs FROM users WHERE user_id = ?", (user_id,)).fetchone()[0] <= 0:
        return await message.answer("❌ У вас закончились покебалы! Купите их в магазине.")
    
    league = min(cursor.execute("SELECT trainer_level FROM users WHERE user_id = ?", (user_id,)).fetchone()[0], len(POKEMONS))
    pokemon = random.choice(POKEMONS[str(league)])
    
    cursor.execute("UPDATE users SET pokeballs = pokeballs - 1 WHERE user_id = ?", (user_id,))
    cursor.execute("INSERT OR IGNORE INTO pokedex (user_id, pokemon_id) VALUES (?, ?)", (user_id, pokemon['id']))
    cursor.execute("UPDATE pokedex SET seen = TRUE WHERE user_id = ? AND pokemon_id = ?", (user_id, pokemon['id']))
    conn.commit()
    
    await message.answer_photo(
        photo=pokemon['image'],
        caption=f"Вы встретили дикого {pokemon['name']}!\nHP: {pokemon['hp']} | ATK: {pokemon['attack']} | DEF: {pokemon['defense']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Поймать!", callback_data=f"catch_{pokemon['id']}")],
            [InlineKeyboardButton(text="Убежать", callback_data="run_away")]
        ])
    )

@dp.callback_query(F.data.startswith("catch_"))
async def catch_pokemon_callback(callback: CallbackQuery):
    pokemon_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    pokemon = next((p for league in POKEMONS.values() for p in league if p['id'] == pokemon_id), None)
    if not pokemon:
        return await callback.answer("❌ Ошибка: покемон не найден")
    
    count = cursor.execute("SELECT count FROM pokemon_counts WHERE user_id = ? AND pokemon_id = ?", 
                         (user_id, pokemon_id)).fetchone()
    if count and count[0] >= 3:
        await callback.message.edit_caption(f"❌ У вас уже есть 3 {pokemon['name']}! Максимальное количество достигнуто.")
        return await callback.answer()
    
    if random.randint(1, 100) <= min(90, max(10, 100 - pokemon['hp'])):
        cursor.executescript(f"""
            INSERT INTO pokemons (owner_id, pokemon_id, name, image, hp, attack, defense)
            VALUES ({user_id}, {pokemon_id}, '{pokemon['name']}', '{pokemon['image']}', {pokemon['hp']}, {pokemon['attack']}, {pokemon['defense']});
            
            INSERT OR IGNORE INTO pokemon_counts (user_id, pokemon_id, count) 
            VALUES ({user_id}, {pokemon_id}, 0);
            
            UPDATE pokemon_counts SET count = count + 1 
            WHERE user_id = {user_id} AND pokemon_id = {pokemon_id};
            
            UPDATE users SET total_pokemons = total_pokemons + 1 WHERE user_id = {user_id};
            
            UPDATE pokedex SET caught = TRUE WHERE user_id = {user_id} AND pokemon_id = {pokemon_id};
        """)
        conn.commit()
        await callback.message.edit_caption(f"🎉 Вы поймали {pokemon['name']}!")
    else:
        await callback.message.edit_caption(f"❌ {pokemon['name']} сбежал! Попробуйте еще раз.")
    await callback.answer()

@dp.callback_query(F.data == "run_away")
async def run_away_callback(callback: CallbackQuery):
    await callback.message.edit_caption("Вы убежали от покемона!")
    await callback.answer()

# ========== МАГАЗИН ==========
@dp.message(F.text == "🛒 Магазин")
async def shop_handler(message: Message):
    await message.answer("🛒 Добро пожаловать в магазин!", reply_markup=get_shop_menu())

@dp.message(F.text == "🎣 Купить покебал (500)")
async def buy_pokeball(message: Message):
    user_id = message.from_user.id
    if cursor.execute("UPDATE users SET balance = balance - 500, pokeballs = pokeballs + 1 WHERE user_id = ? AND balance >= 500", 
                     (user_id,)).rowcount:
        conn.commit()
        await message.answer("🎣 Вы купили 1 покебал!")
    else:
        await message.answer("❌ Недостаточно монет!")
    await message.answer("🛒 Магазин:", reply_markup=get_shop_menu())

@dp.message(F.text == "👨‍🏫 Нанять тренера")
async def hire_trainer_menu(message: Message):
    await message.answer(
        "Выберите тренера:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{trainer[1]} - {trainer[2]} монет (+{trainer[3]}/час)",
                callback_data=f"hire_{trainer[0]}"
            )] for trainer in cursor.execute("SELECT * FROM trainers").fetchall()
        ]))
    )

@dp.callback_query(F.data.startswith("hire_"))
async def hire_trainer(callback: CallbackQuery):
    trainer_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    trainer = cursor.execute("SELECT * FROM trainers WHERE id = ?", (trainer_id,)).fetchone()
    
    if trainer and cursor.execute("""
        UPDATE users SET balance = balance - ?, trainer_id = ?, trainer_level = trainer_level + 1 
        WHERE user_id = ? AND balance >= ?
    """, (trainer[2], trainer_id, user_id, trainer[2])).rowcount:
        conn.commit()
        await callback.message.answer(f"👨‍🏫 Вы наняли тренера {trainer[1]}! Ваш уровень тренера увеличен.")
    else:
        await callback.answer("❌ Недостаточно монет!")
    await callback.answer()

# ========== СТАТИСТИКА ==========
@dp.message(F.text == "📊 Моя статистика")
async def stats_handler(message: Message):
    user_id = message.from_user.id
    data = cursor.execute("""
        SELECT username, balance, pokeballs, total_pokemons, trainer_level
        FROM users WHERE user_id = ?
    """, (user_id,)).fetchone()
    
    if data:
        trainer = cursor.execute("""
            SELECT t.name, t.income FROM users u
            JOIN trainers t ON u.trainer_id = t.id
            WHERE u.user_id = ?
        """, (user_id,)).fetchone()
        
        unique_pokemons = cursor.execute(
            "SELECT COUNT(DISTINCT pokemon_id) FROM pokemons WHERE owner_id = ?", 
            (user_id,)).fetchone()[0]
        
        await message.answer(
            f"📊 Ваша статистика:\n"
            f"👤 Имя: {data[0]}\n💰 Монеты: {data[1]}\n"
            f"🎣 Покебалы: {data[2]}\n🐲 Всего покемонов: {data[3]}\n"
            f"🔄 Уникальных покемонов: {unique_pokemons}\n"
            f"🏅 Уровень тренера: {data[4]}" +
            (f"\n👨‍🏫 Тренер: {trainer[0]} (+{trainer[1]} монет/час)" if trainer else "")
        )

# ========== МОИ ПОКЕМОНЫ ==========
@dp.message(F.text == "📦 Мои покемоны")
async def my_pokemons_handler(message: Message):
    pokemons = cursor.execute("""
        SELECT p.pokemon_id, p.name, p.image, pc.count 
        FROM pokemon_counts pc
        JOIN (SELECT DISTINCT pokemon_id, name, image FROM pokemons WHERE owner_id = ?) p
        ON pc.pokemon_id = p.pokemon_id
        WHERE pc.user_id = ?
        ORDER BY pc.count DESC, p.name
    """, (message.from_user.id, message.from_user.id)).fetchall()
    
    if pokemons:
        await message.answer(
            "📦 Ваши покемоны:\n\n" +
            "\n".join(f"{name} ×{count}" for _, name, _, count in pokemons)
        )
    else:
        await message.answer("❌ У вас пока нет покемонов!")

# ========== ПОКЕДЕКС ==========
@dp.message(F.text == "📘 Покедекс")
async def pokedex_handler(message: Message):
    user_id = message.from_user.id
    current_league = min(cursor.execute(
        "SELECT trainer_level FROM users WHERE user_id = ?", 
        (user_id,)).fetchone()[0], len(POKEMONS))
    
    caught, seen = cursor.execute(
        "SELECT SUM(caught), SUM(seen) FROM pokedex WHERE user_id = ?", 
        (user_id,)).fetchone()
    
    total_in_leagues = sum(len(POKEMONS.get(str(league), [])) for league in range(1, current_league + 1))
    
    await message.answer(
        f"📘 Ваш Покедекс:\n✅ Поймано: {caught or 0}\n"
        f"👀 Видели: {seen or 0}\n🏆 Доступно покемонов: {total_in_leagues}\n"
        f"🔍 Прогресс: {round((caught or 0)/total_in_leagues*100, 1) if total_in_leagues else 0}%"
    )

# ========== СОЗДАНИЕ ПОКЕМОНОВ (АДМИН) ==========
@dp.message(F.text == "Создать покемона")
async def create_pokemon_start(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
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
        await state.update_data(hp=int(message.text))
        await message.answer("Введите атаку покемона:")
        await state.set_state(CreatePokemonState.attack)
    except ValueError:
        await message.answer("❌ Введите число!")

@dp.message(CreatePokemonState.attack)
async def create_pokemon_attack(message: Message, state: FSMContext):
    try:
        await state.update_data(attack=int(message.text))
        await message.answer("Введите защиту покемона:")
        await state.set_state(CreatePokemonState.defense)
    except ValueError:
        await message.answer("❌ Введите число!")

@dp.message(CreatePokemonState.defense)
async def create_pokemon_defense(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        cursor.execute("""
            INSERT INTO custom_pokemons (name, image, hp, attack, defense)
            VALUES (?, ?, ?, ?, ?)
        """, (data['name'], data['image'], data['hp'], data['attack'], int(message.text)))
        conn.commit()
        await message.answer(f"✅ Покемон {data['name']} успешно создан!")
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