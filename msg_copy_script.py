from time import sleep

import telebot


def copy_message(bot: telebot.TeleBot, msg: telebot.types.Message, chat_ids: list, disable_notification=False,
                 keyboard=None):
    last_id = chat_ids[-1]
    if len(chat_ids) > 1:
        chat_ids = chat_ids[:1]
    else:
        chat_ids = []
    if msg.content_type == 'text':
        text = check_msg_entities(msg.entities, msg.html_text)
        for chat_id in chat_ids:
            bot.send_message(chat_id,
                             text=text,
                             parse_mode='html',
                             disable_notification=disable_notification,
                             reply_markup=keyboard
                             )
            sleep(1)
        return bot.send_message(last_id,
                                text=text,
                                parse_mode='html',
                                disable_notification=disable_notification,
                                reply_markup=keyboard
                                )
    else:
        caption = check_msg_entities(msg.entities, msg.html_caption)
        if msg.content_type == 'photo':
            size = msg.photo[-1]
            for chat_id in chat_ids:
                bot.send_photo(chat_id,
                               photo=size.file_id,
                               caption=caption,
                               parse_mode='html',
                               disable_notification=disable_notification,
                               reply_markup=keyboard)
                sleep(1)
            return bot.send_photo(last_id,
                                  photo=size.file_id,
                                  caption=caption,
                                  parse_mode='html',
                                  disable_notification=disable_notification,
                                  reply_markup=keyboard)
        elif msg.content_type == 'audio':
            for chat_id in chat_ids:
                bot.send_audio(chat_id,
                               audio=msg.audio.file_id,
                               caption=caption,
                               parse_mode='html',
                               disable_notification=disable_notification,
                               reply_markup=keyboard)
                sleep(1)
            return bot.send_audio(last_id,
                                  audio=msg.audio.file_id,
                                  caption=caption,
                                  parse_mode='html',
                                  disable_notification=disable_notification,
                                  reply_markup=keyboard)
        elif msg.content_type == 'document':
            for chat_id in chat_ids:
                bot.send_document(chat_id,
                                  data=msg.document.file_id,
                                  caption=caption,
                                  parse_mode='html',
                                  disable_notification=disable_notification,
                                  reply_markup=keyboard)
                sleep(1)
            return bot.send_document(last_id,
                                     data=msg.document.file_id,
                                     caption=caption,
                                     parse_mode='html',
                                     disable_notification=disable_notification,
                                     reply_markup=keyboard)
        elif msg.content_type == 'sticker':
            for chat_id in chat_ids:
                bot.send_sticker(chat_id,
                                 data=msg.sticker.file_id,
                                 disable_notification=disable_notification,
                                 reply_markup=keyboard)
                sleep(1)
            return bot.send_sticker(last_id,
                                    data=msg.sticker.file_id,
                                    disable_notification=disable_notification,
                                    reply_markup=keyboard)
        elif msg.content_type == 'video':
            for chat_id in chat_ids:
                bot.send_video(chat_id,
                               data=msg.video.file_id,
                               caption=caption,
                               parse_mode='html',
                               disable_notification=disable_notification,
                               reply_markup=keyboard)
                sleep(1)
            return bot.send_video(last_id,
                                  data=msg.video.file_id,
                                  caption=caption,
                                  parse_mode='html',
                                  disable_notification=disable_notification,
                                  reply_markup=keyboard)
        elif msg.content_type == 'animation':
            for chat_id in chat_ids:
                bot.send_animation(chat_id,
                                   animation=msg.animation.file_id,
                                   caption=caption,
                                   parse_mode='html',
                                   disable_notification=disable_notification,
                                   reply_markup=keyboard)
                sleep(1)
            return bot.send_animation(last_id,
                                      animation=msg.animation.file_id,
                                      caption=caption,
                                      parse_mode='html',
                                      disable_notification=disable_notification,
                                      reply_markup=keyboard)
        elif msg.content_type == 'voice':
            for chat_id in chat_ids:
                bot.send_voice(chat_id,
                               voice=msg.voice.file_id,
                               caption=caption,
                               parse_mode='html',
                               disable_notification=disable_notification,
                               reply_markup=keyboard)
                sleep(1)
            return bot.send_voice(last_id,
                                  voice=msg.voice.file_id,
                                  caption=caption,
                                  parse_mode='html',
                                  disable_notification=disable_notification,
                                  reply_markup=keyboard)
        elif msg.content_type == 'video_note':
            for chat_id in chat_ids:
                bot.send_video_note(chat_id,
                                    data=msg.video_note.file_id,
                                    disable_notification=disable_notification,
                                    reply_markup=keyboard)
                sleep(1)
            return bot.send_video_note(last_id,
                                       data=msg.video_note.file_id,
                                       disable_notification=disable_notification,
                                       reply_markup=keyboard)
        elif msg.content_type == 'contact':
            for chat_id in chat_ids:
                bot.send_contact(chat_id,
                                 phone_number=msg.contact.phone_number,
                                 first_name=msg.contact.first_name,
                                 last_name=msg.contact.last_name or '',
                                 disable_notification=disable_notification,
                                 reply_markup=keyboard)
                sleep(1)
            return bot.send_contact(last_id,
                                    phone_number=msg.contact.phone_number,
                                    first_name=msg.contact.first_name,
                                    last_name=msg.contact.last_name or '',
                                    disable_notification=disable_notification,
                                    reply_markup=keyboard)
        elif msg.content_type == 'location':
            for chat_id in chat_ids:
                bot.send_location(chat_id,
                                  latitude=msg.location.latitude,
                                  longitude=msg.location.longitude,
                                  disable_notification=disable_notification,
                                  reply_markup=keyboard)
                sleep(1)
            return bot.send_location(last_id,
                                     latitude=msg.location.latitude,
                                     longitude=msg.location.longitude,
                                     disable_notification=disable_notification,
                                     reply_markup=keyboard)
        elif msg.content_type == 'venue':
            for chat_id in chat_ids:
                bot.send_venue(chat_id,
                               latitude=msg.venue.location.latitude,
                               longitude=msg.venue.location.longitude,
                               title=msg.venue.title,
                               address=msg.venue.address,
                               foursquare_id=msg.venue.foursquare_id,
                               disable_notification=disable_notification,
                               reply_markup=keyboard)
                sleep(1)
            return bot.send_venue(last_id,
                                  latitude=msg.venue.location.latitude,
                                  longitude=msg.venue.location.longitude,
                                  title=msg.venue.title,
                                  address=msg.venue.address,
                                  foursquare_id=msg.venue.foursquare_id,
                                  disable_notification=disable_notification,
                                  reply_markup=keyboard)
        elif msg.content_type == 'poll':
            for chat_id in chat_ids:
                bot.forward_message(chat_id, msg.chat.id, msg.message_id)
                sleep(1)
            return bot.forward_message(last_id, msg.chat.id, msg.message_id)
        elif msg.content_type == 'game':
            for chat_id in chat_ids:
                bot.forward_message(chat_id, msg.chat.id, msg.message_id)
                sleep(1)
            return bot.forward_message(last_id, msg.chat.id, msg.message_id)
    raise ValueError('Can\'t copy this message')


def check_msg_entities(entities, html_text):
    return html_text
