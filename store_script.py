import datetime

import requests
from github import Github
from github import InputGitTreeElement
import telebot
from telebot.types import InputMediaDocument
from datetime import date as d
import threading
import sqlite3
import json
import io
import os
import pytz

files_chat_id = None
info_message_id = None
admin_chat_ids = None
start_message_id = None
calendar_message_id = None
calendar_pattern_id = None
calendar_result_texts = None
user_message = None
day_message = None
connection_message = None
started = False

db_connection = sqlite3.connect(":memory:", check_same_thread=False)
db_cursor = db_connection.cursor()
lock_database = threading.Lock()
lock_file_save = threading.Lock()

tz_kiev = pytz.timezone('Europe/Kiev')

data_path = os.path.join(os.path.dirname(__file__), 'bot.properties')

g = Github('BearDimonR', 'dimon2001_bot_SB_temp')
repo = g.get_user().get_repo('files')
commit_message = 'update bot.properties'
commit_lock = threading.Lock()


def restart_bot(bot, msg):
    global files_chat_id
    global user_message
    global day_message
    global connection_message
    global info_message_id
    global admin_chat_ids
    global start_message_id
    global calendar_message_id
    global calendar_pattern_id
    global calendar_result_texts
    if files_chat_id is None:
        global started
        if check_file_properties(bot, msg):
            started = True
            save_properties()
            return
        # set chat_id
        files_chat_id = msg.chat.id
        # send empty info
        info_message_id = bot.send_message(msg.chat.id, 'Information').message_id
        # admin chat
        admin_chat_ids = [msg.chat.id]
        # send empty start
        start_message_id = bot.send_message(msg.chat.id, 'Start info').message_id
        # send default calendar
        calendar_message_id = bot.send_message(msg.chat.id, 'Calendar:\n\n[pattern]\n\nEnd calendar').message_id
        calendar_pattern_id = bot.send_message(msg.chat.id, '***\n\n[date] : [result]\n\n***').message_id
        calendar_result_texts = {5: 'done late', 4: 'done', 3: 'almost done', 2: 'failed', 1: 'not graded',
                                 0: 'not send'}
        # send empty files
        str_data = '[]'
        user_message = bot.send_document(msg.chat.id, io.StringIO(str_data))
        day_message = bot.send_document(msg.chat.id, io.StringIO(str_data))
        connection_message = bot.send_document(msg.chat.id, io.StringIO(str_data))
        # save files
        save_data(bot)
        # properties save
        save_properties()
        # bot was started
        with open(data_path) as json_file:
            bot.send_document(files_chat_id, data=json_file)
        started = True
    elif is_active():
        save_data(bot)
        make_backup(bot)
        files_chat_id = None
        delete_all_data()
        restart_bot(bot, msg)
    else:
        raise FileNotFoundError()


def delete_all_data():
    lock_database.acquire()
    db_cursor.execute("DELETE FROM users")
    db_cursor.execute("DELETE FROM days")
    db_cursor.execute("DELETE FROM user_task_connection")
    db_connection.commit()
    lock_database.release()


def check_file_properties(bot, msg):
    if msg.content_type != 'document':
        return False
    data = json.loads(get_data(bot, msg))
    global files_chat_id
    files_chat_id = data['files_chat_id']
    global info_message_id
    info_message_id = data['info_message_id']
    global admin_chat_ids
    admin_chat_ids = data['admin_chat_ids']
    global start_message_id
    start_message_id = data['start_message_id']
    global calendar_message_id
    calendar_message_id = data['calendar_message_id']
    global calendar_pattern_id
    calendar_pattern_id = data['calendar_pattern_id']
    global calendar_result_texts
    texts = json.loads(data['calendar_result_texts'])
    calendar_result_texts = dict()
    calendar_result_texts[5] = texts['5']
    calendar_result_texts[4] = texts['4']
    calendar_result_texts[3] = texts['3']
    calendar_result_texts[2] = texts['2']
    calendar_result_texts[1] = texts['1']
    calendar_result_texts[0] = texts['0']
    global user_message
    user_message = telebot.types.Message.de_json(data['user_message'])
    global day_message
    day_message = telebot.types.Message.de_json(data['day_message'])
    global connection_message
    connection_message = telebot.types.Message.de_json(data['connection_message'])
    return True


def init_files(bot):
    db_cursor.execute("CREATE TABLE users( chat_id INTEGER PRIMARY KEY, "
                      "date TEXT, "
                      "total_score INTEGER DEFAULT 0)")
    db_cursor.execute("CREATE TABLE days (id INTEGER PRIMARY KEY,"
                      "date TEXT NOT NULL UNIQUE,"
                      "morning_id INTEGER DEFAULT NULL,"
                      "afternoon_id INTEGER DEFAULT NULL,"
                      "evening_id INTEGER DEFAULT NULL,"
                      "task_id INTEGER DEFAULT NULL)")
    db_cursor.execute("CREATE TABLE user_task_connection (id INTEGER PRIMARY KEY,"
                      "chat_id INTEGER NOT NULL,"
                      "day_id INTEGER NOT NULL ,"
                      "complete_state INTEGER DEFAULT 0,"
                      "message_id INTEGER DEFAULT NULL,"
                      "FOREIGN KEY (chat_id) REFERENCES users(chat_id) ON DELETE CASCADE,"
                      "FOREIGN KEY (day_id) REFERENCES days(id) ON DELETE CASCADE)")
    db_connection.commit()
    global started
    try:
        master_ref = repo.get_git_ref('heads/master')
        master_sha = master_ref.object.sha
        parent = repo.get_git_commit(master_sha)
        file_link = 'https://raw.githubusercontent.com/BearDimonR/files/master/bot.properties'.replace('master', parent.raw_data['sha'])
        properties_resp = requests.get(file_link)
        data = json.loads(properties_resp.text)
        global files_chat_id
        files_chat_id = data['files_chat_id']
        global info_message_id
        info_message_id = data['info_message_id']
        global admin_chat_ids
        admin_chat_ids = data['admin_chat_ids']
        global start_message_id
        start_message_id = data['start_message_id']
        global calendar_message_id
        calendar_message_id = data['calendar_message_id']
        global calendar_pattern_id
        calendar_pattern_id = data['calendar_pattern_id']
        global calendar_result_texts
        texts = json.loads(data['calendar_result_texts'])
        calendar_result_texts = dict()
        calendar_result_texts[5] = texts['5']
        calendar_result_texts[4] = texts['4']
        calendar_result_texts[3] = texts['3']
        calendar_result_texts[2] = texts['2']
        calendar_result_texts[1] = texts['1']
        calendar_result_texts[0] = texts['0']
        global user_message
        user_message = telebot.types.Message.de_json(data['user_message'])
        global day_message
        day_message = telebot.types.Message.de_json(data['day_message'])
        global connection_message
        connection_message = telebot.types.Message.de_json(data['connection_message'])
        load_data(bot)
        started = True
        check_connections(bot)
        bot.send_message(files_chat_id, 'bot started')
    except KeyError:
        started = False


def commit_to_git():
    commit_lock.acquire()
    master_ref = repo.get_git_ref('heads/master')
    master_sha = master_ref.object.sha
    base_tree = repo.get_git_tree(master_sha)
    element_list = list()
    with open(data_path) as input_file:
        data = input_file.read()
    element = InputGitTreeElement('bot.properties', '100644', 'blob', data)
    element_list.append(element)
    tree = repo.create_git_tree(element_list, base_tree)
    parent = repo.get_git_commit(master_sha)
    commit = repo.create_git_commit(commit_message, tree, [parent])
    master_ref.edit(commit.sha)
    commit_lock.release()


def make_backup(bot):
    save_data(bot)
    bot.send_message(files_chat_id, '.............\nBackUp ' + str(datetime.datetime.now().astimezone(tz_kiev)))
    bot.forward_message(files_chat_id, files_chat_id, user_message.message_id)
    bot.forward_message(files_chat_id, files_chat_id, day_message.message_id)
    bot.forward_message(files_chat_id, files_chat_id, connection_message.message_id)
    with open(data_path) as json_file:
        bot.send_document(files_chat_id, data=json_file)
    bot.send_message(files_chat_id, '...................................')


def load_data(bot):
    users = json.loads(get_data(bot, user_message))
    db_cursor.executemany("INSERT INTO users VALUES (?,?,?)", users)
    db_connection.commit()
    days = json.loads(get_data(bot, day_message))
    db_cursor.executemany("INSERT INTO days VALUES (?,?,?,?,?,?)", days)
    db_connection.commit()
    conns = json.loads(get_data(bot, connection_message))
    db_cursor.executemany("INSERT INTO user_task_connection VALUES (?,?,?,?,?)", conns)
    db_connection.commit()


def save_properties():
    lock_file_save.acquire()
    with open(data_path, 'w') as bot_file:
        json.dump({'files_chat_id': files_chat_id,
                   'info_message_id': info_message_id,
                   'admin_chat_ids': admin_chat_ids,
                   'start_message_id': start_message_id,
                   'calendar_message_id': calendar_message_id,
                   'calendar_pattern_id': calendar_pattern_id,
                   'calendar_result_texts': json.dumps(calendar_result_texts),
                   'user_message': user_message.json,
                   'day_message': day_message.json,
                   'connection_message': connection_message.json
                   }, bot_file)
    commit_to_git()
    lock_file_save.release()


def has_admin_perm(chat_id):
    return chat_id in admin_chat_ids


def add_admin(chat_id):
    admin_chat_ids.append(chat_id)
    threading.Thread(target=save_properties).start()


def is_active():
    return started


def is_authorized(chat_id):
    lock_database.acquire()
    sql = "SELECT chat_id FROM users WHERE chat_id = " + str(chat_id)
    db_cursor.execute(sql)
    user = db_cursor.fetchall()
    lock_database.release()
    return len(user) != 0


def check_connections(bot):
    lock_database.acquire()
    db_cursor.execute("SELECT date,id FROM days")
    days = db_cursor.fetchall()
    days_dict = {}
    for day in days:
        days_dict[day[0]] = day[1]
    db_cursor.execute("SELECT chat_id, day_id FROM user_task_connection")
    connections = db_cursor.fetchall()
    conn_dict = {}
    for conn in connections:
        try:
            conn_dict[conn[0]].append(conn[1])
        except KeyError:
            conn_dict[conn[0]] = [conn[1]]
    add = []
    db_cursor.execute("SELECT * FROM users")
    users = db_cursor.fetchall()
    now = datetime.datetime.now().astimezone(tz_kiev).date()
    delta = datetime.timedelta(days=1)
    for user in users:
        chat_id = user[0]
        date = d.fromisoformat(user[1])
        while date <= now:
            try:
                day_id = days_dict[str(date)]
            except KeyError:
                day_id = change_day(bot, [str(date)])
                days_dict[str(date)] = day_id
            if day_id not in conn_dict[chat_id]:
                add.append((chat_id, day_id))
            date += delta
    if len(add) != 0:
        db_cursor.executemany("INSERT INTO user_task_connection (chat_id, day_id) VALUES (?,?)", add)
        db_connection.commit()
        threading.Thread(target=save_connection, args=(bot,)).start()
    lock_database.release()


def add_connections(bot):
    tomorrow = datetime.datetime.now().astimezone(tz_kiev)
    tomorrow += datetime.timedelta(days=1)
    tomorrow = str(tomorrow.date())
    day_id = get_day_id(tomorrow)
    if day_id is None:
        day_id = change_day(bot, [tomorrow])
    chat_ids = get_users_chat_ids()
    lock_database.acquire()
    db_cursor.executemany("INSERT INTO user_task_connection (chat_id, day_id) VALUES (?,?)",
                          [(chat_id, day_id) for chat_id in chat_ids])
    db_connection.commit()
    lock_database.release()
    threading.Thread(target=save_connection, args=(bot,)).start()


def get_chat_id():
    return files_chat_id


def get_info_msg_id():
    return info_message_id


def get_start_msg_id():
    return start_message_id


def get_users_chat_ids():
    lock_database.acquire()
    db_cursor.execute("SELECT chat_id FROM users")
    res = [msg_id[0] for msg_id in db_cursor.fetchall()]
    lock_database.release()
    return res


def get_data(bot, msg):
    file_id_info = bot.get_file(msg.document.file_id)
    res = bot.download_file(file_id_info.file_path)
    return res


def get_day_id(date=datetime.datetime.now().astimezone(tz_kiev).date()):
    lock_database.acquire()
    db_cursor.execute("SELECT id FROM days WHERE date=?", [date])
    res = db_cursor.fetchall()
    lock_database.release()
    if len(res) == 0:
        return None
    return res[0][0]


def get_day(date=datetime.datetime.now().astimezone(tz_kiev).date()):
    lock_database.acquire()
    db_cursor.execute("SELECT date, morning_id, afternoon_id, evening_id, task_id FROM days WHERE date=?", [date])
    res = db_cursor.fetchall()
    lock_database.release()
    if len(res) == 0:
        return [date]
    return list(res[0])


def get_calendar_message_id():
    return calendar_message_id


def get_calendar_pattern_id():
    return calendar_pattern_id


def get_calendar_results():
    return calendar_result_texts


def get_user_result(chat_id, date):
    conn = get_user_task_conn(chat_id, date)
    if conn is None:
        raise ValueError()
    return calendar_result_texts[conn[3]]


def get_calendar_results_text():
    return str(json.dumps(calendar_result_texts)) \
        .replace('{', '') \
        .replace('}', '') \
        .replace('\\', '') \
        .replace('"', '') \
        .replace(', ', '\n') \
        .replace('\'5\'', 'done late:') \
        .replace('\'4\':', 'done: ') \
        .replace('\'3\':', 'almost done: ') \
        .replace('\'2\':', 'failed: ') \
        .replace('\'1\':', 'not graded: ') \
        .replace('\'0\':', 'not send: ')


def get_user_date_result(chat_id):
    lock_database.acquire()
    db_cursor.execute("SELECT date, complete_state FROM user_task_connection "
                      "LEFT JOIN days d on user_task_connection.day_id = d.id WHERE chat_id=?", [chat_id])
    res = db_cursor.fetchall()
    lock_database.release()
    return res


def get_user_task_conn(chat_id, date):
    lock_database.acquire()
    db_cursor.execute(
        "SELECT user_task_connection.id, chat_id, day_id, complete_state, message_id FROM user_task_connection "
        "JOIN days d ON user_task_connection.day_id = d.id WHERE date=? AND chat_id=?",
        [date, chat_id])
    res = db_cursor.fetchall()
    lock_database.release()
    if len(res) == 0:
        return None
    return list(res[0])


def get_user_task_conn_check(date):
    lock_database.acquire()
    db_cursor.execute(
        "SELECT user_task_connection.id, chat_id, day_id, complete_state, message_id FROM user_task_connection "
        "JOIN days d ON user_task_connection.day_id = d.id WHERE date=? AND complete_state=1",
        [date])
    res = db_cursor.fetchone()
    lock_database.release()
    return res


def get_dates_for_check():
    lock_database.acquire()
    db_cursor.execute("SELECT date FROM days JOIN user_task_connection utc on days.id = utc.day_id"
                      " WHERE complete_state=1")
    res = db_cursor.fetchall()
    lock_database.release()
    return [i[0] for i in res]


def save_data(bot):
    save_users(bot)
    save_days(bot)
    save_connection(bot)


def save_users(bot):
    lock_database.acquire()
    sql = "SELECT * FROM users "
    db_cursor.execute(sql)
    users = db_cursor.fetchall()
    lock_database.release()
    try:
        str_data = json.dumps(users)
        global user_message
        lock_file_save.acquire()
        user_message = bot.edit_message_media(
            InputMediaDocument(io.StringIO(str_data)),
            files_chat_id,
            user_message.message_id)
        lock_file_save.release()
        save_properties()
    except Exception as ex:
        print(ex)
        raise ex


def save_days(bot):
    lock_database.acquire()
    sql = "SELECT * FROM days "
    db_cursor.execute(sql)
    days = db_cursor.fetchall()
    lock_database.release()
    try:
        str_data = json.dumps(days)
        global day_message
        lock_file_save.acquire()
        day_message = bot.edit_message_media(
            InputMediaDocument(io.StringIO(str_data)),
            files_chat_id,
            day_message.message_id)
        lock_file_save.release()
        save_properties()
    except Exception as ex:
        print(ex)
        raise ex


def save_connection(bot):
    lock_database.acquire()
    sql = "SELECT * FROM user_task_connection"
    db_cursor.execute(sql)
    conn = db_cursor.fetchall()
    lock_database.release()
    try:
        global connection_message
        str_data = json.dumps(conn)
        lock_file_save.acquire()
        connection_message = bot.edit_message_media(
            InputMediaDocument(io.StringIO(str_data)),
            files_chat_id,
            connection_message.message_id)
        lock_file_save.release()
        save_properties()
    except Exception as ex:
        print(ex)
        raise ex


def save_information(bot, msg_id):
    global info_message_id
    info_message_id = msg_id
    threading.Thread(target=save_properties).start()


def save_start(bot, msg_id):
    global start_message_id
    start_message_id = msg_id
    threading.Thread(target=save_properties).start()


def save_calendar_message(bot, msg_id):
    global calendar_message_id
    calendar_message_id = msg_id
    threading.Thread(target=save_properties).start()


def save_calendar_pattern(bot, msg_id):
    global calendar_pattern_id
    calendar_pattern_id = msg_id
    threading.Thread(target=save_properties).start()


def save_calendar_result(msg):
    global calendar_result_texts
    text = str(msg.text).replace('\n', '').replace(']', '').split('[')
    text.remove('')
    calendar_result_texts[5] = text[0].split(':')[1]
    calendar_result_texts[4] = text[1].split(':')[1]
    calendar_result_texts[3] = text[2].split(':')[1]
    calendar_result_texts[2] = text[3].split(':')[1]
    calendar_result_texts[1] = text[4].split(':')[1]
    calendar_result_texts[0] = text[5].split(':')[1]
    threading.Thread(target=save_properties).start()


def save_task_hand_over(bot, chat_id, date, msg_id):
    if not is_authorized(chat_id):
        register_user(bot, chat_id)
    lock_database.acquire()
    db_cursor.execute(
        "SELECT user_task_connection.id, chat_id, task_id, complete_state, message_id FROM user_task_connection"
        " LEFT JOIN days d ON user_task_connection.day_id = d.id"
        " WHERE chat_id=? AND date=?", [chat_id, date])
    res = db_cursor.fetchall()[0]
    conn_id, chat_id, task_id, complete_state, message_id = res
    lock_database.release()
    if complete_state != 4:
        lock_database.acquire()
        db_cursor.execute("UPDATE user_task_connection SET complete_state=?, message_id=? WHERE id=?",
                          [1, msg_id, conn_id])
        db_connection.commit()
        lock_database.release()
        threading.Thread(target=save_connection, args=(bot,)).start()
    else:
        raise Exception()


def save_task_result(bot, conn_id, mark):
    lock_database.acquire()
    db_cursor.execute("UPDATE user_task_connection SET complete_state=? WHERE id=?", [mark, conn_id])
    db_connection.commit()
    lock_database.release()
    threading.Thread(target=save_connection, args=(bot,)).start()


def register_user(bot, chat_id):
    now = datetime.datetime.now().astimezone(tz_kiev).date()
    lock_database.acquire()
    db_cursor.execute("INSERT INTO users (chat_id, date) VALUES (?,?)", [chat_id, now])
    db_connection.commit()
    lock_database.release()
    day_id = get_day_id(now)
    if day_id is None:
        change_day(bot, [now])
        day_id = get_day_id(now)
    if get_user_task_conn(chat_id, str(now)) is None:
        lock_database.acquire()
        db_cursor.execute("INSERT INTO user_task_connection (chat_id, day_id) VALUES (?,?)", [chat_id, day_id])
        db_connection.commit()
        lock_database.release()
        threading.Thread(target=save_connection, args=(bot,)).start()
    threading.Thread(target=save_users, args=(bot,)).start()


def change_day(bot, day_to_change):
    day = get_day(day_to_change[0])
    res = None
    lock_database.acquire()
    if len(day) == 1:
        if len(day_to_change) == 1:
            db_cursor.execute("INSERT INTO days (date) VALUES (?)", day_to_change)
        else:
            db_cursor.execute("INSERT INTO days (date, morning_id, afternoon_id, evening_id, task_id)"
                              " VALUES (?,?,?,?,?)", day_to_change)
        res = db_cursor.lastrowid
    else:
        db_cursor.execute("UPDATE days SET morning_id=?, afternoon_id=?, evening_id=?, task_id=? WHERE date=?",
                          day_to_change[1:] + day_to_change[:1])
    db_connection.commit()
    lock_database.release()
    threading.Thread(target=save_days, args=(bot,)).start()
    return res
