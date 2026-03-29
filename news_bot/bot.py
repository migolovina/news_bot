import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import random
import json
import os
from datetime import datetime, timedelta
import pytz
import feedparser
from bs4 import BeautifulSoup
import threading
import time as time_module
import hashlib
VK_TOKEN = "vk1.a.A5RF6R-wav2nh0nbE1sgDHUj0ftbcG60XF-xHqz04saJzs09QtMsqxR2LNA0fux3nEWhqVbvMUIlvIUxDGHDCY7m-leu9RjgmixtjCptMdVNSQAXvfipdVn2SWvhECiVVPY4u77ySQjed0daU-cRoUm5XPh8HHyECG2P7xgXTJWYt13GaamtNenJJai6sGwlKuh8usEhFF-iwfjTcZnLJg"
GROUP_ID = 237132707
MOSCOW_TZ = pytz.timezone('Europe/Moscow')
RSS_SOURCES = [
    'https://lenta.ru/rss/news',
    'https://lenta.ru/rss/news/politics',
    'https://tass.ru/rss/v2/politics.xml',
    'https://ria.ru/export/rss2/politics/index.html',
]
TIME_SLOTS = ["8:00","9:00","10:00","11:00","12:00","13:00","14:00","15:00","16:00","17:00","18:00","19:00","20:00","21:00"]
USERS_FILE = "vk_users.json"
SENT_NEWS_FILE = "sent_news.json"
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}
def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
def add_user(users, user_id):
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {
            'subscribed': False,
            'send_time': "19:00",
            'created_at': datetime.now(MOSCOW_TZ).isoformat()
        }
        save_users(users)
    return users[user_id_str]
def load_sent_news():
    if os.path.exists(SENT_NEWS_FILE):
        with open(SENT_NEWS_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()
def save_sent_news(sent_news):
    with open(SENT_NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(sent_news), f, ensure_ascii=False)
def clean_old_sent_news():
    sent_news = load_sent_news()
    pass
def get_news_id(title, link):
    unique_string = f"{title}{link}"
    return hashlib.md5(unique_string.encode()).hexdigest()
def mark_news_as_sent(news_ids):
    sent_news = load_sent_news()
    sent_news.update(news_ids)
    save_sent_news(sent_news)
def get_news():
    news_list = []
    sent_news = load_sent_news()
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                for entry in feed.entries[:3]:
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    if not title or not link:
                        continue
                    news_id = get_news_id(title, link)
                    if news_id in sent_news:
                        continue
                    description = entry.get('description', '')
                    if description:
                        soup = BeautifulSoup(description, 'html.parser')
                        description = soup.get_text()[:200]
                    
                    news_list.append({
                        'id': news_id,
                        'title': title,
                        'link': link,
                        'description': description
                    })
        except Exception as e:
            print(f"Ошибка {url}: {e}")
    unique_news = []
    seen_titles = set()
    for news in news_list:
        if news['title'] not in seen_titles:
            seen_titles.add(news['title'])
            unique_news.append(news)
    return unique_news[:5]
def send_message(vk, user_id, text):
    try:
        vk.messages.send(
            user_id=user_id,
            message=text,
            random_id=random.randint(1, 2**31)
        )
    except Exception as e:
        print(f"Ошибка отправки: {e}")
def send_news(vk, user_id):
    news_list = get_news()
    if not news_list:
        send_message(vk, user_id, "Новых политических новостей пока нет.")
        return
    news_ids = [news['id'] for news in news_list]
    mark_news_as_sent(news_ids)
    for news in news_list:
        text = f"{news['title']}\n\n"
        if news['description']:
            text += f"{news['description']}\n\n"
        text += f"{news['link']}"
        send_message(vk, user_id, text)
        time_module.sleep(0.5)
    send_message(vk, user_id, f"Отправлено {len(news_list)} новых новостей")
def send_daily_news():
    print(f"\n[{datetime.now(MOSCOW_TZ).strftime('%H:%M:%S')}] Запуск ежедневной рассылки")
    news_list = get_news()
    if not news_list:
        print("  Новых новостей нет")
        return
    print(f"  Найдено {len(news_list)} новых новостей")
    news_ids = [news['id'] for news in news_list]
    mark_news_as_sent(news_ids)
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    users = load_users()
    current_time = datetime.now(MOSCOW_TZ).strftime("%H:%M")
    sent_count = 0
    for user_id_str, user_data in users.items():
        if user_data.get('subscribed') and user_data.get('send_time') == current_time:
            try:
                user_id = int(user_id_str)
                print(f"  Отправка пользователю {user_id}")
                send_message(vk, user_id, f"Доброго времени суток! Свежие политические новости на {datetime.now(MOSCOW_TZ).strftime('%d.%m.%Y')}:\n")
                for news in news_list:
                    text = f"{news['title']}\n\n"
                    if news['description']:
                        text += f"{news['description']}\n\n"
                    text += f"{news['link']}"
                    send_message(vk, user_id, text)
                    time_module.sleep(0.5)
                sent_count += 1
                time_module.sleep(1)
            except Exception as e:
                print(f"Ошибка {user_id}: {e}")
    print(f"Отправлено {sent_count} пользователям")
def scheduler_thread():
    last_sent_time = {}
    while True:
        current_time = datetime.now(MOSCOW_TZ).strftime("%H:%M")
        if current_time in TIME_SLOTS:
            if last_sent_time.get(current_time) != datetime.now(MOSCOW_TZ).strftime("%Y-%m-%d %H:%M"):
                last_sent_time[current_time] = datetime.now(MOSCOW_TZ).strftime("%Y-%m-%d %H:%M")
                send_daily_news()
        time_module.sleep(60)
def main():
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    users = load_users()
    sent_count = len(load_sent_news())
    print(f"Загружено пользователей: {len(users)}")
    print(f"Отправлено новостей всего: {sent_count}")
    print(f"Время по Москве: {datetime.now(MOSCOW_TZ).strftime('%H:%M:%S')}")
    scheduler = threading.Thread(target=scheduler_thread, daemon=True)
    scheduler.start()
    print("\n📨 Бот готов к работе!")
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            msg = event.obj.message
            user_id = msg['from_id']
            text = msg['text'].lower().strip()
            add_user(users, user_id)
            user = users[str(user_id)]
            if text in ['/start', 'начать', 'привет']:
                response = (
                    "Привет! Я бот для политических новостей!\n\n"
                    "/news - получить новые новости сейчас\n"
                    "/subscribe - подписаться на рассылку\n"
                    "/unsubscribe - отписаться\n"
                    "/time - показать время\n"
                    "/time 19:00 - установить время\n"
                    "/help - помощь\n\n"
                )
                send_message(vk, user_id, response)
            elif text == '/news':
                send_news(vk, user_id)
            elif text == '/subscribe':
                if not user['subscribed']:
                    user['subscribed'] = True
                    save_users(users)
                    response = f"Вы подписаны на рассылку!\nНовости будут приходить каждый день в {user['send_time']} (МСК)\n📰 Приходят только новые новости"
                else:
                    response = "Вы уже подписаны на рассылку!"
                send_message(vk, user_id, response)
            elif text == '/unsubscribe':
                if user['subscribed']:
                    user['subscribed'] = False
                    save_users(users)
                    response = "Вы отписаны от рассылки"
                else:
                    response = "Вы не подписаны на рассылку"
                send_message(vk, user_id, response)
            elif text.startswith('/time'):
                parts = text.split()
                if len(parts) == 1:
                    response = f"Твое время рассылки: {user['send_time']} (МСК)\nИзменить: /time 20:00\n\nДоступное время: {', '.join(TIME_SLOTS)}"
                else:
                    new_time = parts[1]
                    if new_time in TIME_SLOTS:
                        user['send_time'] = new_time
                        save_users(users)
                        response = f"Время рассылки изменено на {new_time} (МСК)"
                    else:
                        response = f"Неверное время. Доступно: {', '.join(TIME_SLOTS)}"
                send_message(vk, user_id, response)
            elif text == '/help':
                response = (
                    "Помощь\n\n"
                    "/news - получить новые новости сейчас\n"
                    "/subscribe - подписаться на рассылку\n"
                    "/unsubscribe - отписаться\n"
                    "/time - показать текущее время рассылки\n"
                    "/time 19:00 - установить время рассылки\n\n"
                    f"Доступное время (МСК): {', '.join(TIME_SLOTS)}\n"
                    f"Новости: {len(RSS_SOURCES)} источников\n"
                )
                send_message(vk, user_id, response)
            else:
                pass
if __name__ == '__main__':
    main()