import telebot
from telebot import types
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import requests

API_TOKEN = '7572209825:AAEKYKQqasaFY6al6B2GfJYNR-RSbLhzinM'
bot = telebot.TeleBot(API_TOKEN)

Base = declarative_base()
engine = create_engine('sqlite:///tg.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()

class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    file_name = Column(String)
    description = Column(Text)
    date_uploaded = Column(DateTime)

    def __repr__(self):
        return f"<File(user_id={self.user_id}, file_name='{self.file_name}', date_uploaded='{self.date_uploaded}')>"

class Note(Base):
    __tablename__ = 'notes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    title = Column(String)
    content = Column(Text)
    date_created = Column(DateTime)

Base.metadata.create_all(engine)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Это мультифункциональный бот. Вы можете загружать файлы, вести заметки и многое другое. Чтобы узнать весь функционал, введите /help")

@bot.message_handler(commands=['help'])
def help_message(message):
    help_text = (
        "/start - Начать работу\n"
        "/help - Справка\n"
        "/files - Показать ваши файлы\n"
        "/addnote - Добавить заметку\n"
        "/notes - Показать заметки\n"
        "/deletefile - Удалить файл\n"
        "/deletenote - Удалить заметку\n"
        "/quote - Получить случайную цитату\n"
        "/setname - Сохранить имя\n"
        "/getname - Получить имя"
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(content_types=['audio'])
def handle_audio(message):
    user_id = message.from_user.id
    file_info = bot.get_file(message.audio.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    save_dir = 'downloads'
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    file_path = os.path.join(save_dir, message.audio.file_name)
    with open(file_path, 'wb') as new_file:
        new_file.write(downloaded_file)

    new_file_record = File(
        user_id=user_id,
        file_name=message.audio.file_name,
        description='Музыкальный файл',
        date_uploaded=datetime.now()
    )
    session.add(new_file_record)
    session.commit()

    bot.reply_to(message, f"Файл {message.audio.file_name} успешно сохранен!")

@bot.message_handler(commands=['files'])
def list_files(message):
    user_id = message.from_user.id
    files = session.query(File).filter_by(user_id=user_id).all()

    if not files:
        bot.reply_to(message, "У вас пока нет загруженных файлов.")
    else:
        response = "Ваши файлы:\n" + '\n'.join([f"{f.file_name} (загружен: {f.date_uploaded.strftime('%Y-%m-%d %H:%M:%S')})" for f in files])
        bot.reply_to(message, response)

@bot.message_handler(commands=['deletefile'])
def delete_file(message):
    msg = bot.send_message(message.chat.id, "Введите имя файла для удаления:")
    bot.register_next_step_handler(msg, process_delete_file)

def process_delete_file(message):
    user_id = message.from_user.id
    file_name = message.text.strip()
    file_record = session.query(File).filter_by(user_id=user_id, file_name=file_name).first()

    if file_record:
        session.delete(file_record)
        session.commit()
        file_path = os.path.join('downloads', file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
        bot.reply_to(message, f"Файл {file_name} удален.")
    else:
        bot.reply_to(message, "Файл не найден.")

@bot.message_handler(commands=['addnote'])
def add_note_start(message):
    msg = bot.send_message(message.chat.id, "Введите заголовок заметки:")
    bot.register_next_step_handler(msg, process_note_title)

note_data = {}

def process_note_title(message):
    note_data[message.from_user.id] = {'title': message.text.strip()}
    msg = bot.send_message(message.chat.id, "Введите содержимое заметки:")
    bot.register_next_step_handler(msg, process_note_content)

def process_note_content(message):
    user_id = message.from_user.id
    note_data[user_id]['content'] = message.text.strip()
    new_note = Note(
        user_id=user_id,
        title=note_data[user_id]['title'],
        content=note_data[user_id]['content'],
        date_created=datetime.now()
    )
    session.add(new_note)
    session.commit()
    bot.reply_to(message, "Заметка сохранена!")

@bot.message_handler(commands=['notes'])
def list_notes(message):
    user_id = message.from_user.id
    notes = session.query(Note).filter_by(user_id=user_id).all()
    if not notes:
        bot.reply_to(message, "У вас пока нет заметок.")
    else:
        response = "Ваши заметки:\n" + '\n'.join([f"{n.title}: {n.content}" for n in notes])
        bot.reply_to(message, response)

@bot.message_handler(commands=['deletenote'])
def delete_note_start(message):
    msg = bot.send_message(message.chat.id, "Введите заголовок заметки для удаления:")
    bot.register_next_step_handler(msg, process_delete_note)

def process_delete_note(message):
    user_id = message.from_user.id
    title = message.text.strip()
    note = session.query(Note).filter_by(user_id=user_id, title=title).first()
    if note:
        session.delete(note)
        session.commit()
        bot.reply_to(message, "Заметка удалена.")
    else:
        bot.reply_to(message, "Заметка не найдена.")

@bot.message_handler(commands=['quote'])
def send_quote(message):
    try:
        # Используем другой API для цитат, чтобы избежать SSL проблем
        response = requests.get('https://api.forismatic.com/api/1.0/?method=getQuote&lang=ru&format=json')
        if response.status_code == 200:
            data = response.json()
            text = data.get('quoteText', 'Цитата не найдена').strip()
            author = data.get('quoteAuthor', 'Неизвестный автор').strip()
            bot.reply_to(message, f"Случайная цитата:\n{text} — {author}")
        else:
            bot.reply_to(message, "Не удалось получить цитату.")
    except Exception as e:
        bot.reply_to(message, "Произошла ошибка при получении цитаты. Пожалуйста, попробуйте позже.")


user_context = {}

@bot.message_handler(commands=['setname'])
def set_name(message):
    msg = bot.send_message(message.chat.id, "Введите ваше имя:")
    bot.register_next_step_handler(msg, process_name)

def process_name(message):
    user_context[message.from_user.id] = {'name': message.text.strip()}
    bot.reply_to(message, f"Имя сохранено: {message.text.strip()}")

@bot.message_handler(commands=['getname'])
def get_name(message):
    user_data = user_context.get(message.from_user.id)
    if user_data and 'name' in user_data:
        bot.reply_to(message, f"Ваше имя: {user_data['name']}")
    else:
        bot.reply_to(message, "Имя еще не установлено. Используйте команду /setname.")

bot.infinity_polling()
