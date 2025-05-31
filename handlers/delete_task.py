from telebot import types
from db.repository import delete_task_by_message_id

def register(bot):
    @bot.message_handler(commands=['delete'])
    def handle_delete_command(message):
        if not message.reply_to_message:
            bot.reply_to(message, "Эту команду нужно использовать в ответ на сообщение с задачей.")
            return

        replied_message_id = message.reply_to_message.message_id

        deleted = delete_task_by_message_id(replied_message_id)

        if deleted:
            bot.reply_to(message, "Задача успешно удалена.")
            try:
                bot.delete_message(message.chat.id, replied_message_id)
            except:
                pass
        else:
            bot.reply_to(message, "Задача не найдена.")