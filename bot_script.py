import sys
from store_script import *
from calendar_script import *
from msg_copy_script import *

import schedule
import atexit
import telebot
import threading
import hashlib
import regex as re
import os
import pytz
import logging
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date as d

tz_kiev = pytz.timezone('Europe/Kiev')


TOKEN = '1153271700:AAHiKc2o1vsZ0nKS8BuMoM3WMOoGYplG3zA'

bot_instance = telebot.TeleBot(TOKEN)
restart_password = '5a82d6497f6e915d57609916f2423e2b'
admin_password = '9f176ec57c09dcc7e9f082cae646403a'

messages_to_delete = []

server = Flask(__name__)

cron = BackgroundScheduler(daemon=True)

splitter = lambda lst, sz: [lst[i:i + sz] for i in range(0, len(lst), sz)]


@server.route('/' + TOKEN, methods=['POST'])
def get_message():
    updates_list = splitter([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))], 30)
    for updates in updates_list:
        bot_instance.process_new_updates(updates)
        sleep(1)
    return "!", 200


@server.route("/")
def web_hook():
    bot_instance.remove_webhook()
    bot_instance.set_webhook(url='https://agile-headland-39464.herokuapp.com/' + TOKEN)
    return "!", 200


@server.errorhandler(telebot.apihelper.ApiException)
def error_handler(error):
    sleep(10)
    bot_instance.send_message(get_chat_id(), '#ERROR\n' + str(error))


@cron.scheduled_job('cron', hour=5, minute=30)
def morning_msg():
    send_scheduled_msgs(1)


@cron.scheduled_job('cron', hour=12)
def afternoon_msg():
    send_scheduled_msgs(2)


@cron.scheduled_job('cron', hour=18)
def evening_msg():
    add_connections(bot_instance)
    send_scheduled_msgs(3)


def launch_server():
    init_files(bot_instance)
    server.logger.setLevel(logging.WARNING)
    cron.start()
    atexit.register(lambda: end_func())
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))


def end_func():
    cron.shutdown(wait=False)
    save_data(bot_instance)
    make_backup(bot_instance)


def launch():
    global bot_instance
    bot_instance.remove_webhook()
    schedule_start()
    init_files(bot_instance)
    while True:
        is_alive = True
        schedule_thread = threading.Thread(target=schedule_check, name='schedule_thread', args=(lambda: is_alive,))
        try:
            schedule_thread.start()
            bot_instance.polling(none_stop=True, timeout=150)
        except BaseException or telebot.apihelper.ApiException:
            is_alive = False
            schedule_thread.join()
            bot_instance.stop_bot()
            e = sys.exc_info()[0]
            sleep(5)
            bot_instance = telebot.TeleBot(TOKEN)
            bot_instance.send_message(get_chat_id(), '#ERROR\n\n' + str(e))
            make_backup(bot_instance)
            save_data(bot_instance)


def schedule_check(is_alive):
    while is_alive():
        schedule.run_pending()
        sleep(1)


def schedule_start():
    schedule.every(6).hours.do(make_backup, bot_instance)
    schedule.every().day.at("08:30").do(send_scheduled_msgs, 1)  # 8:30
    schedule.every().day.at("15:00").do(send_scheduled_msgs, 2)  # 15:00
    schedule.every().day.at("21:40").do(send_scheduled_msgs, 3)  # 21:30
    schedule.every().day.at("21:41").do(add_connections, bot_instance)


def start_scheduled_thread(n):
    threading.Thread(target=send_scheduled_msgs, args=n).start()


def send_scheduled_msgs(n):
    day = get_day()
    if len(day) == 1 or day[n] is None:
        return
    ids = get_users_chat_ids()
    if len(ids) == 0:
        return
    # TODO SEND PROBLEM
    forwarded_msg = bot_instance.forward_message(get_chat_id(), get_chat_id(), day[n])
    copy_message(bot_instance, forwarded_msg, ids)
    bot_instance.delete_message(forwarded_msg.chat.id, forwarded_msg.message_id)


def check_active(msg):
    if is_active():
        return True
    else:
        bot_instance.send_message(chat_id=msg.chat.id,
                                  text='Bot is not activated. Contact administrator for details.')
        return False


@bot_instance.message_handler(commands=['info'])
def info_command(msg):
    if check_active(msg):
        send_copy(msg.chat.id, get_chat_id(), get_info_msg_id())


@bot_instance.message_handler(commands=['today', 'calendar'])
def check_auth(msg):
    if not is_authorized(msg.chat.id):
        start_command(msg)
    else:
        if '/today' in msg.text:
            today_command(msg)
        elif '/calendar' in msg.text:
            calendar_command(msg)


@bot_instance.message_handler(commands=['start'])
def start_command(msg):
    if str(msg.text) == '/start admin':
        password_msg = bot_instance.send_message(chat_id=msg.chat.id, text='Password:')
        bot_instance.clear_step_handler_by_chat_id(msg.chat.id)
        bot_instance.register_next_step_handler(password_msg, check_restart_pass)
    elif not check_active(msg):
        pass
    elif str(msg.text) == '/start admin panel':
        if has_admin_perm(msg.chat.id):
            show_admin_panel(msg.chat.id)
        else:
            password_msg = bot_instance.send_message(chat_id=msg.chat.id, text='Password:')
            bot_instance.clear_step_handler_by_chat_id(msg.chat.id)
            bot_instance.register_next_step_handler(password_msg, check_admin_pass)
    else:
        send_copy(msg.chat.id, get_chat_id(), get_start_msg_id(),
                  keyboard=telebot.types.InlineKeyboardMarkup().row(
                      telebot.types.InlineKeyboardButton(text='  Зрозуміло, погнали!   ', callback_data='accept_rules')))


def send_copy(chat_id, from_chat_id, message_id, disable_notification=False, keyboard=None):
    forwarded_msg = bot_instance.forward_message(from_chat_id, from_chat_id, message_id)
    msg = copy_message(bot_instance, forwarded_msg, [chat_id], disable_notification=disable_notification,
                       keyboard=keyboard)
    bot_instance.delete_message(from_chat_id, forwarded_msg.message_id)
    return msg


def show_admin_panel(chat_id):
    if has_admin_perm(chat_id):
        bot_instance.send_message(chat_id=chat_id, text='****** Admin panel ******',
                                  reply_markup=telebot.types.InlineKeyboardMarkup()
                                  .row(
                                      telebot.types.InlineKeyboardButton(text='Edit  /info', callback_data='edit info'),
                                      telebot.types.InlineKeyboardButton(text='Edit  /calendar',
                                                                         callback_data='edit calendar'))
                                  .row(
                                      telebot.types.InlineKeyboardButton(text='Edit  Days', callback_data='edit days'),
                                      telebot.types.InlineKeyboardButton(text='Edit  /start',
                                                                         callback_data='edit start'))
                                  .row(
                                      telebot.types.InlineKeyboardButton(text='Send message',
                                                                         callback_data='send message'),
                                      telebot.types.InlineKeyboardButton(text='Check Tasks',
                                                                         callback_data='check tasks'))
                                  .row(
                                      telebot.types.InlineKeyboardButton(text='Undo',
                                                                         callback_data='clear next handlers'),
                                      telebot.types.InlineKeyboardButton(text='Close', callback_data='close')))


def check_restart_pass(msg):
    if hashlib.md5(msg.text.encode('utf8')).hexdigest() == restart_password:
        bot_instance.send_message(chat_id=msg.chat.id, text='File:')
        bot_instance.clear_step_handler_by_chat_id(msg.chat.id)
        bot_instance.register_next_step_handler(msg, restart_with_property)
    else:
        bot_instance.send_message(chat_id=msg.chat.id, text='Wrong password.')


def restart_with_property(msg):
    restart_bot(bot_instance, msg)


def check_admin_pass(msg):
    if hashlib.md5(msg.text.encode('utf8')).hexdigest() == admin_password:
        add_admin(bot_instance, msg.chat.id)
        show_admin_panel(msg.chat.id)
    else:
        bot_instance.send_message(chat_id=msg.chat.id, text='Wrong password.')


@bot_instance.callback_query_handler(lambda query: query.data == 'accept_rules')
def accept_handler(callback_query):
    bot_instance.edit_message_reply_markup(chat_id=callback_query.message.chat.id,
                                           message_id=callback_query.message.message_id,
                                           reply_markup=None)
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True) \
        .row(telebot.types.KeyboardButton(text='/info'),
             telebot.types.KeyboardButton(text='/today'),
             telebot.types.KeyboardButton(text='/calendar'))
    if not is_authorized(callback_query.message.chat.id):
        bot_instance.send_message(chat_id=callback_query.message.chat.id,
                                  text='Команди розблоковані!',
                                  reply_markup=keyboard)
        threading.Thread(target=register_user, args=(bot_instance, callback_query.message.chat.id,)).start()
    else:
        bot_instance.send_message(chat_id=callback_query.message.chat.id,
                                  text='Вітаю з поверненням!',
                                  reply_markup=keyboard)


def calendar_command(msg):
    dates_res = get_user_date_result(msg.chat.id)
    forwarded_msg = bot_instance.forward_message(get_chat_id(), get_chat_id(), get_calendar_message_id())
    messages_to_delete.append(forwarded_msg)
    pattern_msg = bot_instance.forward_message(get_chat_id(), get_chat_id(), get_calendar_pattern_id())
    messages_to_delete.append(pattern_msg)
    threading.Thread(target=delete_all).start()
    pattern_text = check_msg_entities(pattern_msg.entities, pattern_msg.html_text)
    results_dict = get_calendar_results()
    text = check_msg_entities(forwarded_msg.entities, forwarded_msg.html_text)
    pattern = '\n\n'
    for date_res in dates_res:
        pattern += pattern_text \
            .replace('[date]', date_res[0]) \
            .replace('[result]', str(results_dict[date_res[1]])) + '\n\n'
    text = text.replace('[pattern]', pattern)
    bot_instance.send_message(msg.chat.id, text, parse_mode='html', reply_markup=telebot.types.InlineKeyboardMarkup()
                              .row(telebot.types.InlineKeyboardButton('Закрити',
                                                                      callback_data='close select date'),
                                   telebot.types.InlineKeyboardButton('Обрати дату',
                                                                      callback_data='calendar select date')))


@bot_instance.callback_query_handler(lambda query: 'close select date' == str(query.data))
def close_select_date(query):
    bot_instance.edit_message_reply_markup(query.message.chat.id, query.message.message_id,
                                           reply_markup=None)


@bot_instance.callback_query_handler(lambda query: 'calendar select date' in str(query.data))
def calendar_select_date(query):
    if 'calendar select date' == query.data:
        dates_res = get_user_date_result(query.message.chat.id)
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.row_width = 4
        for date_res in dates_res:
            date = str(date_res[0])
            keyboard.add(telebot.types.InlineKeyboardButton(date, callback_data='calendar select date:' + date))
        bot_instance.edit_message_reply_markup(query.message.chat.id, query.message.message_id, reply_markup=keyboard)
    else:
        bot_instance.edit_message_reply_markup(query.message.chat.id, query.message.message_id,
                                               reply_markup=telebot.types.InlineKeyboardMarkup()
                                               .row(telebot.types.InlineKeyboardButton('Закрити',
                                                                                       callback_data='close select date'),
                                                    telebot.types.InlineKeyboardButton('Обрати дату',
                                                                                       callback_data='calendar select date')))
        calendar_day_info(query.message.chat.id, str(query.data).split(':')[1])


def calendar_day_info(chat_id, date=str(datetime.datetime.now().astimezone(tz_kiev).date())):
    day = get_day(date)
    if len(day) == 1 or day[4] is None:
        bot_instance.send_message(chat_id, 'Сьогодні завдань немає!')
    else:
        keyboard = telebot.types.InlineKeyboardMarkup() \
            .row(telebot.types.InlineKeyboardButton('Відправити пруф',
                                                    callback_data='hand over task:'
                                                                  + date))
        connection = get_user_task_conn(chat_id, date)
        if connection is not None and connection[4] is not None:
            if connection[3] is not None and connection[3] == 4:
                keyboard = None
            bot_instance.send_message(chat_id, 'День ' + date + ':')
            send_copy(chat_id, get_chat_id(), day[4], keyboard=keyboard)
            bot_instance.send_message(chat_id, 'Твоя відповідь:')
            bot_instance.forward_message(chat_id, get_chat_id(), connection[4])
            bot_instance.send_message(chat_id, 'Статус: ' + get_user_result(chat_id, date))
        else:
            send_copy(chat_id, get_chat_id(), day[4], keyboard=keyboard)


def today_command(msg):
    calendar_day_info(msg.chat.id)


@bot_instance.callback_query_handler(lambda query: 'hand over task' in str(query.data))
def hand_over_task(query):
    connection = get_user_task_conn(query.message.chat.id, str(query.data).split(':')[1])
    if connection is None or connection[3] == 4 or connection[3] == 5:
        bot_instance.edit_message_reply_markup(query.message.chat.id, query.message.message_id, reply_markup=None)

        bot_instance.answer_callback_query(query.id, text="Пруф не можна відправити!")
        return
    bot_instance.edit_message_reply_markup(query.message.chat.id,
                                           query.message.message_id,
                                           reply_markup=None)
    bot_instance.send_message(chat_id=query.message.chat.id,
                              text='Чекаю на твій пруф:',
                              reply_markup=None)
    bot_instance.clear_step_handler_by_chat_id(query.message.chat.id)
    bot_instance.register_next_step_handler(query.message, hand_over_task_save, str(query.data).split(':')[1])
    bot_instance.answer_callback_query(query.id)


def hand_over_task_save(msg, date):
    forwarded_msg = bot_instance.forward_message(get_chat_id(), msg.chat.id, msg.message_id)
    save_task_hand_over(bot_instance, msg.chat.id, date, forwarded_msg.message_id)
    bot_instance.send_message(chat_id=msg.chat.id,
                              text='Єєє🔥\nЗавдання відправлено і знаходиться на перевірці!\n'
                                   'Ти прийняв цей виклик і зробив крок до трішечки оновленої версії себе😎\n\n'
                                   'Сподіваємося, було цікаво та , а при виконанні ніхто не постраждав. '
                                   '\n\nЧарівного настрою⚡️')


@bot_instance.callback_query_handler(lambda query: 'edit days' in str(query.data))
def edit_days(query):
    if query.data == 'edit days':
        messages_to_delete.append(bot_instance.edit_message_text(chat_id=query.message.chat.id,
                                                                 text='Days Edit\n\nSelect day:',
                                                                 message_id=query.message.message_id,
                                                                 reply_markup=create_calendar()))
        return
    data = str(query.data).split(':')
    messages_to_delete.append(bot_instance.send_message(query.message.chat.id,
                                                        'Send new ' + data[1] + ':'))
    bot_instance.clear_step_handler_by_chat_id(query.message.chat.id)
    bot_instance.register_next_step_handler(query.message, edit_day, str(query.data).split(':')[1], json.loads(data[2]))
    bot_instance.answer_callback_query(query.id)


@bot_instance.callback_query_handler(lambda query: is_calendar_callback(query.data))
def calendar(query):
    date = process_calendar_selection(bot_instance, query)
    if date is not None:
        bot_instance.answer_callback_query(query.id, text="Selected:" + str(date.date()))
        if 'Days Edit' in str(query.message.text):
            selected_day = get_day(str(date.date()))
            json_day = json.dumps(selected_day)
            messages_to_delete.append(
                bot_instance.edit_message_text(chat_id=query.message.chat.id,
                                               text='Days Edit\n\nSelected day: '
                                                    + str(date.date()),
                                               message_id=query.message.message_id,
                                               reply_markup=telebot.types.InlineKeyboardMarkup()
                                               .row(telebot.types.InlineKeyboardButton(
                                                   text='Edit  Morning',
                                                   callback_data='edit days:morning:' + json_day),
                                                   telebot.types.InlineKeyboardButton(
                                                       text='Edit  Afternoon',
                                                       callback_data='edit days:afternoon:' + json_day),
                                                   telebot.types.InlineKeyboardButton(
                                                       text='Edit  Evening',
                                                       callback_data='edit days:evening:' + json_day))
                                               .row(
                                                   telebot.types.InlineKeyboardButton(text='Back',
                                                                                      callback_data='back'),
                                                   telebot.types.InlineKeyboardButton(
                                                       text='Edit  Task',
                                                       callback_data='edit days:task:' + json_day))
                                               ))
            if len(selected_day) != 1:
                send_day_info(selected_day[1], query.message.chat.id, 'Morning:')
                send_day_info(selected_day[2], query.message.chat.id, 'Afternoon:')
                send_day_info(selected_day[3], query.message.chat.id, 'Evening:')
                send_day_info(selected_day[4], query.message.chat.id, 'Task:')


def edit_day(msg, day_part, selected_day):
    if day_part == 'morning':
        n = 1
    elif day_part == 'afternoon':
        n = 2
    elif day_part == 'evening':
        n = 3
    elif day_part == 'task':
        n = 4
    else:
        raise AttributeError()
    if len(selected_day) == 1:
        for i in range(4):
            selected_day.append(None)
    if selected_day[n] is not None:
        bot_instance.delete_message(get_chat_id(), selected_day[n])
    threading.Thread(target=delete_all).start()
    forwarded_msg = bot_instance.forward_message(get_chat_id(), msg.chat.id, msg.message_id)
    selected_day[n] = forwarded_msg.message_id
    threading.Thread(target=change_day, args=(bot_instance, selected_day,)).start()
    show_admin_panel(msg.chat.id)


def send_day_info(msg_id, chat_id, text):
    if msg_id is not None:
        messages_to_delete.append(bot_instance.send_message(chat_id, text))
        messages_to_delete.append(send_copy(chat_id, get_chat_id(), msg_id))


@bot_instance.callback_query_handler(lambda query: 'back' == query.data)
def back(query):
    clear_before(query)
    show_admin_panel(query.message.chat.id)


@bot_instance.callback_query_handler(lambda query: 'clear next handlers' == query.data)
def clear_before(query):
    threading.Thread(target=delete_all).start()
    bot_instance.clear_reply_handlers_by_message_id(query.message.chat.id)
    bot_instance.clear_step_handler_by_chat_id(query.message.chat.id)
    bot_instance.answer_callback_query(query.id)


def delete_all():
    new_list = messages_to_delete.copy()
    messages_to_delete.clear()
    new_list.reverse()
    for i in new_list:
        try:
            bot_instance.delete_message(i.chat.id, i.message_id)
        except telebot.apihelper.ApiException:
            pass


@bot_instance.callback_query_handler(lambda query: 'edit info' in query.data)
def edit_info(query):
    if query.data == 'edit info':
        messages_to_delete.append(
            bot_instance.edit_message_text(chat_id=query.message.chat.id,
                                           message_id=query.message.message_id,
                                           text='Information edit:',
                                           reply_markup=telebot.types.InlineKeyboardMarkup()
                                           .row(telebot.types.InlineKeyboardButton(text='Back',
                                                                                   callback_data='back'),
                                                telebot.types.InlineKeyboardButton(text='Edit',
                                                                                   callback_data='edit info:message'))))
        messages_to_delete.append(send_copy(query.message.chat.id, get_chat_id(), get_info_msg_id()))
        bot_instance.answer_callback_query(query.id)
    elif query.data == 'edit info:message':
        messages_to_delete.append(bot_instance.send_message(chat_id=query.message.chat.id, text='Send new:'))
        bot_instance.clear_step_handler_by_chat_id(query.message.chat.id)
        bot_instance.register_next_step_handler(query.message, edit_info_save)
        bot_instance.answer_callback_query(query.id)


def edit_info_save(msg):
    threading.Thread(target=delete_all).start()
    forwarded_msg = bot_instance.forward_message(get_chat_id(), msg.chat.id, msg.message_id)
    save_information(bot_instance, forwarded_msg.message_id)
    show_admin_panel(msg.chat.id)


@bot_instance.callback_query_handler(lambda query: 'edit start' in query.data)
def edit_start(query):
    if query.data == 'edit start':
        messages_to_delete.append(
            bot_instance.edit_message_text(chat_id=query.message.chat.id,
                                           message_id=query.message.message_id,
                                           text='Start edit:',
                                           reply_markup=telebot.types.InlineKeyboardMarkup()
                                           .row(telebot.types.InlineKeyboardButton(text='Back',
                                                                                   callback_data='back'),
                                                telebot.types.InlineKeyboardButton(text='Edit',
                                                                                   callback_data='edit start:message'))))
        messages_to_delete.append(send_copy(query.message.chat.id, get_chat_id(), get_start_msg_id()))
        bot_instance.answer_callback_query(query.id)
    elif query.data == 'edit start:message':
        messages_to_delete.append(bot_instance.send_message(chat_id=query.message.chat.id, text='Send new:'))
        bot_instance.clear_step_handler_by_chat_id(query.message.chat.id)
        bot_instance.register_next_step_handler(query.message, edit_start_save)
        bot_instance.answer_callback_query(query.id)


def edit_start_save(msg):
    threading.Thread(target=delete_all).start()
    forwarded_msg = bot_instance.forward_message(get_chat_id(), msg.chat.id, msg.message_id)
    save_start(bot_instance, forwarded_msg.message_id)
    show_admin_panel(msg.chat.id)


@bot_instance.callback_query_handler(lambda query: 'edit calendar' in query.data)
def edit_calendar(query, chat_id=None):
    if chat_id is not None or query.data == 'edit calendar':
        chat_id = chat_id if query is None else query.message.chat.id
        if query is not None:
            bot_instance.delete_message(query.message.chat.id, query.message.message_id)
        messages_to_delete.append(
            bot_instance.send_message(
                chat_id=chat_id,
                text='Calendar edit:',
                reply_markup=telebot.types.InlineKeyboardMarkup()
                    .row(telebot.types.InlineKeyboardButton(text='Edit message',
                                                            callback_data='edit calendar:message'),
                         telebot.types.InlineKeyboardButton(text='Edit pattern',
                                                            callback_data='edit calendar:pattern'))
                    .row(telebot.types.InlineKeyboardButton(text='Back',
                                                            callback_data='back'),
                         telebot.types.InlineKeyboardButton(text='Edit result',
                                                            callback_data='edit calendar:result'))
            )
        )
        send_calendar_info(chat_id, get_calendar_message_id(), 'Calendar message:')
        send_calendar_info(chat_id, get_calendar_pattern_id(), 'Calendar pattern:')
        messages_to_delete.append(bot_instance.send_message(chat_id,
                                                            'Result messages:\n' + get_calendar_results_text()))
    elif query.data == 'edit calendar:message':
        messages_to_delete.append(bot_instance.send_message(chat_id=query.message.chat.id,
                                                            text='Send new message in form:\nText\n[pattern]\nText\n'))
        bot_instance.clear_step_handler_by_chat_id(query.message.chat.id)
        bot_instance.register_next_step_handler(query.message, edit_calendar_message_save)
        bot_instance.answer_callback_query(query.id)
    elif query.data == 'edit calendar:pattern':
        messages_to_delete.append(bot_instance.send_message(chat_id=query.message.chat.id,
                                                            text='Send new message in form:\n\nFor example:'
                                                                 '\n****\n[date] : [result]\n****\n'))
        bot_instance.clear_step_handler_by_chat_id(query.message.chat.id)
        bot_instance.register_next_step_handler(query.message, edit_calendar_pattern_save)
        bot_instance.answer_callback_query(query.id)
    elif query.data == 'edit calendar:result':
        messages_to_delete.append(bot_instance.send_message(chat_id=query.message.chat.id,
                                                            text='Send new message in form:\n\n'
                                                                 '[done late:message]\n'
                                                                 '[done:message]\n'
                                                                 '[almost done:message]\n'
                                                                 '[failed:message]\n'
                                                                 '[not graded:message]\n'
                                                                 '[not send:message]\n'))
        bot_instance.clear_step_handler_by_chat_id(query.message.chat.id)
        bot_instance.register_next_step_handler(query.message, edit_calendar_result_save)
        bot_instance.answer_callback_query(query.id)


def send_calendar_info(chat_id, msg_id, text):
    messages_to_delete.append(bot_instance.send_message(chat_id, text))
    messages_to_delete.append(send_copy(chat_id, get_chat_id(), msg_id))


def edit_calendar_message_save(msg):
    if '\n[pattern]\n' in msg.text:
        delete = threading.Thread(target=delete_all)
        delete.start()
        forwarded_msg = bot_instance.forward_message(get_chat_id(), msg.chat.id, msg.message_id)
        save_calendar_message(bot_instance, forwarded_msg.message_id)
        delete.join()
        edit_calendar(None, msg.chat.id)
    else:
        messages_to_delete.append(bot_instance.send_message(msg.chat.id,
                                                            'Wrong format (must consist [pattern]'))


def edit_calendar_pattern_save(msg):
    if '[date]' in msg.text and '[result]' in msg.text:
        delete = threading.Thread(target=delete_all)
        delete.start()
        forwarded_msg = bot_instance.forward_message(get_chat_id(), msg.chat.id, msg.message_id)
        save_calendar_pattern(bot_instance, forwarded_msg.message_id)
        delete.join()
        edit_calendar(None, msg.chat.id)
    else:
        messages_to_delete.append(bot_instance.send_message(msg.chat.id,
                                                            'Wrong format (must consist [date] and [result])'))


def edit_calendar_result_save(msg):
    if re.fullmatch(
            r'\[done late:[\S\s]+\]\n'
            r'\[done:[\S\s]+\]\n'
            r'\[almost done:[\S\s]+\]\n'
            r'\[failed:[\S\s]+\]\n'
            r'\[not graded:[\S\s]+\]\n'
            r'\[not send:[\S\s]+\]', str(msg.text)):
        forwarded_msg = bot_instance.forward_message(get_chat_id(), msg.chat.id, msg.message_id)
        save_calendar_result(bot_instance, forwarded_msg)
        messages_to_delete.append(forwarded_msg)
        delete = threading.Thread(target=delete_all)
        delete.start()
        delete.join()
        edit_calendar(None, msg.chat.id)
    else:
        messages_to_delete.append(bot_instance.send_message(msg.chat.id,
                                                            'Wrong format\n'
                                                            '[done late:message]\n'
                                                            '[done:message]\n'
                                                            '[almost done:message]\n'
                                                            '[failed:message]\n'
                                                            '[not graded:message]\n'
                                                            '[not send:message]\n\n'))


@bot_instance.callback_query_handler(lambda query: 'close' == query.data)
def close_admin_panel(query):
    bot_instance.delete_message(query.message.chat.id, query.message.message_id)


@bot_instance.callback_query_handler(lambda query: 'send message' == query.data)
def send_message_command(query):
    messages_to_delete.append(bot_instance.send_message(chat_id=query.message.chat.id, text='Message:'))
    bot_instance.clear_step_handler_by_chat_id(query.message.chat.id)
    bot_instance.register_next_step_handler(query.message, send_message_thread, query)
    bot_instance.answer_callback_query(query.id)


def send_message_thread(msg, query):
    bot_instance.delete_message(query.message.chat.id, query.message.message_id)
    threading.Thread(target=send_message_job, args=(msg,)).start()
    show_admin_panel(msg.chat.id)
    delete_all()


def send_message_job(msg):
    ids = get_users_chat_ids()
    if len(ids) == 0:
        return
    copy_message(bot_instance, msg, ids)


@bot_instance.callback_query_handler(lambda query: 'check tasks' in query.data)
def check_tasks(query):
    if 'check tasks' == query.data:
        delete_all()
        keyboard = telebot.types.InlineKeyboardMarkup(2)
        for date in get_dates_for_check():
            keyboard.add(telebot.types.InlineKeyboardButton(date, callback_data='check tasks:' + date))
        keyboard.add(telebot.types.InlineKeyboardButton('Back', callback_data='back tasks'))
        bot_instance.edit_message_text(chat_id=query.message.chat.id,
                                       message_id=query.message.message_id,
                                       text='Check tasks\nSelect date for check:',
                                       reply_markup=keyboard)
    else:
        bot_instance.edit_message_text('Оцініть:',
                                       query.message.chat.id,
                                       query.message.message_id)
        date = str(query.data).split(':')[1]
        query.data = 'check next tasks:' + date
        check_next_tasks(query)


@bot_instance.callback_query_handler(lambda query: 'check save' in query.data)
def check_save(query):
    spl = str(query.data).split(':')
    chat_id = spl[4]
    date = spl[3]
    conn_id = spl[2]
    mark = int(spl[1])
    # TODO check this
    if mark == 4 and d.fromisoformat(date) < datetime.datetime.now().astimezone(tz_kiev).date():
        mark = 5
    save_task_result(bot_instance, conn_id, mark)
    bot_instance.answer_callback_query(query.id, text="Успішно")
    bot_instance.send_message(chat_id,
                              text='Завдання ' + date + ' перевірено. Статус: ' + get_calendar_results()[mark])
    query.data = 'check next tasks:' + date
    check_next_tasks(query)


@bot_instance.callback_query_handler(lambda query: 'check next tasks' in query.data)
def check_next_tasks(query):
    delete_all()
    date = str(query.data).split(':')[1]
    day = get_day()
    connection = get_user_task_conn_check(date)
    keyboard = telebot.types.InlineKeyboardMarkup()
    if connection is not None:
        keyboard.row(
            telebot.types.InlineKeyboardButton('Done', callback_data='check save:4:' + str(
                connection[0]) + ':' + date + ':' + str(connection[1])),
            telebot.types.InlineKeyboardButton('Almost',
                                               callback_data='check save:3:' + str(
                                                   connection[0]) + ':' + date + ':' + str(connection[1])),
            telebot.types.InlineKeyboardButton('Failed',
                                               callback_data='check save:2:' + str(
                                                   connection[0]) + ':' + date + ':' + str(connection[1])))
    keyboard.row(telebot.types.InlineKeyboardButton('Back', callback_data='check tasks'))
    bot_instance.edit_message_reply_markup(query.message.chat.id,
                                           query.message.message_id,
                                           reply_markup=keyboard)
    if connection is not None:
        messages_to_delete.append(send_copy(query.message.chat.id, get_chat_id(), day[4]))
        messages_to_delete.append(bot_instance.forward_message(query.message.chat.id, get_chat_id(), connection[4]))


@bot_instance.callback_query_handler(lambda query: 'back tasks' in query.data)
def back_tasks(query):
    bot_instance.delete_message(query.message.chat.id, query.message.message_id)
    back(query)


if __name__ == '__main__':
     launch()
    #launch_server()
