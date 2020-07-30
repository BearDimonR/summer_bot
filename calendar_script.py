import calendar
import datetime

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


def create_callback_data(action, year, month, day):
    return ";".join(["CALENDAR", action, str(year), str(month), str(day)])


def separate_callback_data(data):
    return data.split(";")


def is_calendar_callback(data):
    return separate_callback_data(data)[0] == 'CALENDAR'


def create_calendar(year=None, month=None):
    now = datetime.datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    data_ignore = create_callback_data("IGNORE", year, month, 0)
    keyboard = []
    # First row - Month and Year
    row = [InlineKeyboardButton(calendar.month_name[month] + " " + str(year), callback_data=data_ignore)]
    keyboard.append(row)
    # Second row - Week Days
    row = []
    for day in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]:
        row.append(InlineKeyboardButton(day, callback_data=data_ignore))
    keyboard.append(row)

    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data=data_ignore))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=create_callback_data("DAY", year, month, day)))
        keyboard.append(row)
    # Last row - Buttons
    row = [InlineKeyboardButton("<", callback_data=create_callback_data("PREV-MONTH", year, month, day)),
           InlineKeyboardButton("Back", callback_data='back'),
           InlineKeyboardButton(">", callback_data=create_callback_data("NEXT-MONTH", year, month, day))]
    keyboard.append(row)
    markup = InlineKeyboardMarkup()
    for row in keyboard:
        markup.row(*row)
    return markup


def process_calendar_selection(bot, query):
    ret_data = None
    (cal, action, year, month, day) = separate_callback_data(query.data)
    curr = datetime.datetime(int(year), int(month), 1)
    if action == "IGNORE":
        bot.answer_callback_query(callback_query_id=query.id)
    elif action == "DAY":
        bot.edit_message_text(text=query.message.text,
                              chat_id=query.message.chat.id,
                              message_id=query.message.message_id
                              )
        ret_data = datetime.datetime(int(year), int(month), int(day))
    elif action == "PREV-MONTH":
        pre = curr - datetime.timedelta(days=1)
        bot.edit_message_text(text=query.message.text,
                              chat_id=query.message.chat.id,
                              message_id=query.message.message_id,
                              reply_markup=create_calendar(int(pre.year), int(pre.month)))
    elif action == "NEXT-MONTH":
        ne = curr + datetime.timedelta(days=31)
        bot.edit_message_text(text=query.message.text,
                              chat_id=query.message.chat.id,
                              message_id=query.message.message_id,
                              reply_markup=create_calendar(int(ne.year), int(ne.month)))
    else:
        bot.answer_callback_query(callback_query_id=query.id, text="Something went wrong!")
    return ret_data
