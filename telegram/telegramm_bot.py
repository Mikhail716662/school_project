import logging
from datetime import datetime

import pytz
from telegram import ReplyKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler
import main1
from telegram.config import BOT_TOKEN


TASK_NOTIFICATIONS = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Словарь для хранения задач и времени уведомлений


async def keyboard1():
    """Создает клавиатуру с новыми кнопками для управления напоминаниями"""
    reply_keyboard = [
        ['/update', '/view_all_tasks'],
        ['/new_task', '/stop_new_task'],
        ['/change_task', '/stop_change'],
        ['/delete_task', '/stop_del_task'],
        ['/help', '/delete_all_tasks']
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    return markup


async def start(update, context):
    """Отправляет сообщение когда получена команда /start"""
    markup = await keyboard1()
    user = update.effective_user
    await update.message.reply_html(
        rf"Привет, {user.mention_html()}! Я task-bot."
        rf"Я умею просматривать задачи, добавлять, удалять, изменять их и устанавливать напоминания.",
        reply_markup=markup
    )
    res = main1.cur.execute("SELECT * FROM database").fetchall()
    for i in res:
        if i[1] not in TASK_NOTIFICATIONS:
            TASK_NOTIFICATIONS[i[1]] = []
        TASK_NOTIFICATIONS[i[1]].append(i[2])
    # Запускаем проверку уведомлений
    if 'job' not in context.chat_data:
        context.job_queue.run_repeating(
            check_task_notifications,
            interval=60,  # Проверка каждую минуту
            first=0,
            chat_id=update.effective_chat.id,
            name=str(update.effective_chat.id))
        context.chat_data['job'] = True


async def delete_all_tasks(update, context):
    await update.message.reply_text(
        "Вы уверены, что хотите удалить все задачи?")
    return 1


async def delete_all_1(update, context):
    if update.message.text.strip().lower() == 'да':
        main1.cur.execute("DELETE FROM database")
        await update.message.reply_text(
            "Все задачи удалены")
        TASK_NOTIFICATIONS.clear()
    return ConversationHandler.END


async def stop_del_all_tasks(update, context):
    await update.message.reply_text("Удаление всех задач прервано!")
    context.user_data.clear()
    return ConversationHandler.END


async def update(update, context):
    res = main1.cur.execute("SELECT * FROM database").fetchall()
    for i in res:
        if i[1] not in TASK_NOTIFICATIONS:
            TASK_NOTIFICATIONS[i[1]] = []
        TASK_NOTIFICATIONS[i[1]].append(i[2])
    # Запускаем проверку уведомлений
    if 'job' not in context.chat_data:
        context.job_queue.run_repeating(
            check_task_notifications,
            interval=60,  # Проверка каждую минуту
            first=0,
            chat_id=update.effective_chat.id,
            name=str(update.effective_chat.id))
        context.chat_data['job'] = True
    await update.message.reply_text(
        "Данные обновлены")


async def check_task_notifications(context):
    """Проверяет задачи и отправляет уведомления"""
    now = datetime.now(pytz.timezone('Europe/Moscow')).strftime("%d.%m.%Y %H:%M")
    for task, times in TASK_NOTIFICATIONS.items():
        if now in times:
            await context.bot.send_message(
                chat_id=context.job.chat_id,
                text=f"⏰ Напоминание! Задача '{task}' должна быть выполнена!"
            )
            logger.info(f"Sent reminder for task: {task}")


# Новые команды для работы с напоминаниями
async def set_reminder(update, context):
    """Начинает процесс установки напоминания"""
    await update.message.reply_text(
        "Введите название задачи для напоминания:")
    return 1


async def get_reminder_time(update, context):
    """Получает время напоминания"""
    task_name = update.message.text
    context.user_data['reminder_task'] = task_name
    await update.message.reply_text(
        "Введите дату и время напоминания (в формате ДД.ММ.ГГГГ Ч:ММ):")
    return 2


async def save_reminder(update, context):
    """Сохраняет напоминание"""
    time_str = update.message.text
    task_name = context.user_data['reminder_task']
    try:
        # Проверяем корректность формата времени
        datetime.strptime(time_str, "%d.%m.%Y %H:%M")
        if task_name not in TASK_NOTIFICATIONS:
            TASK_NOTIFICATIONS[task_name] = []
        TASK_NOTIFICATIONS[task_name].append(time_str)

        await update.message.reply_text(
            f"Напоминание для задачи '{task_name}' на {time_str} установлено!")
    except ValueError:
        await update.message.reply_text(
            "Неверный формат даты! Используйте ДД.ММ.ГГГГ Ч:ММ")

    context.user_data.clear()
    return ConversationHandler.END


async def view_reminders(update, context):
    """Показывает все установленные напоминания"""
    if not TASK_NOTIFICATIONS:
        await update.message.reply_text("Нет активных напоминаний.")
        return

    message = "Активные напоминания:\n"
    for task, times in TASK_NOTIFICATIONS.items():
        message += f"\nЗадача: {task}\n"
        for time_str in times:
            message += f"  - {time_str}\n"

    await update.message.reply_text(message)


async def stop_reminder(update, context):
    """Прерывает установку напоминания"""
    await update.message.reply_text("Установка напоминания прервана!")
    context.user_data.clear()
    return ConversationHandler.END


# Оригинальные функции из вашего кода (без изменений)
async def help(update, context):
    await update.message.reply_text("Отправьте на почту aksios705@yandex.ru ваш вопрос. "
                                    "Вам ответит первый освободившийся оператор")


async def view_all_tasks(update, context):
    res = main1.cur.execute("SELECT * FROM database").fetchall()
    if len(res) != 0:
        for i in res:
            await update.message.reply_text(f'*id*: {str(i[0])}\n*название*: {i[1]}\n*время уведомления*: '
                                            f'{"/".join(i[2].split('.'))}\n*статус*: {i[3]}',
                                            parse_mode="MarkdownV2")
    else:
        await update.message.reply_text('У вас пока нет задач')
    return ConversationHandler.END


async def new_task(update, context):
    await update.message.reply_text("Введите название задачи:")
    return 1


async def first_response(update, context):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Введите дату и время уведомления (в формате ДД.ММ.ГГГГ Ч:ММ):")
    return 2


async def get_status(update, context):
    context.user_data['date'] = update.message.text
    try:
        datetime.strptime(context.user_data['date'], "%d.%m.%Y %H:%M")
        await update.message.reply_text("Введите статус задачи:")
        return 3
    except Exception:
        await update.message.reply_text("Неверный формат даты! Используйте ДД.ММ.ГГГГ Ч:ММ")
        return 2


async def write_in(update, context):
    context.user_data['status'] = update.message.text
    if context.user_data['status'] == '' or context.user_data['status'].isspace():
        await update.message.reply_text("Статус задачи не может быть пустым!")
        return 2
    main1.cur.execute("""
                INSERT INTO database (название, время_уведомления, статус)
                VALUES (?, ?, ?)
            """, (context.user_data['name'], context.user_data['date'], context.user_data['status']))
    main1.con.commit()
    if context.user_data['name'] not in TASK_NOTIFICATIONS:
        TASK_NOTIFICATIONS[context.user_data['name']] = []
    TASK_NOTIFICATIONS[context.user_data['name']].append(context.user_data['date'])
    await update.message.reply_text("Задача успешно добавлена!")
    context.user_data.clear()
    return ConversationHandler.END


async def stop_new_task(update, context):
    await update.message.reply_text("Создание новой задачи приостановлено!")
    context.user_data.clear()
    return ConversationHandler.END


async def delete_task(update, context):
    await update.message.reply_text("Введите id задачи или её название:")
    return 1


async def first_response_del(update, context):
    if update.message.text.isdigit():
        context.user_data['id'] = int(update.message.text)
        try:
            res = main1.cur.execute("SELECT * FROM database WHERE id = ?", (context.user_data['id'],)).fetchone()
            await update.message.reply_text(f'*id*: {str(res[0])}\n*название*: {res[1]}\n*время уведомления*: '
                                        f'{"/".join(res[2].split('.'))}\n*статус*: {res[3]}',
                                        parse_mode="MarkdownV2")
            context.user_data['date'] = res[2]
            context.user_data['name'] = res[1]
            await update.message.reply_text(
                'Чтобы удалить задачу, отправьте слово "да" и она удалится.')
        except Exception:
            await update.message.reply_text(
                'Вы ввели несуществующий id. Попробуйте запустить команду и ввести данные заново')
            return ConversationHandler.END
    else:
        name = update.message.text
        context.user_data['name'] = name
        try:
            res = main1.cur.execute(
                f"SELECT * FROM database where название like '%{name.lower()}%' or название like "
                f"'%{name.capitalize()}%'").fetchall()
            if len(res) == 1:
                await update.message.reply_text(f'*id*: {str(res[0])}\n*название*: {res[1]}\n*время уведомления*: '
                                            f'{"/".join(res[2].split('.'))}\n*статус*: {res[3]}',
                                            parse_mode="MarkdownV2")
                context.user_data['date'] = res[2]
                context.user_data['id'] = int(res[0])
                await update.message.reply_text(
                    'Чтобы удалить задачу, отправьте слово "да"')
            else:
                for i in res:
                    await update.message.reply_text(f'*id*: {str(i[0])}\n*название*: {i[1]}\n*время уведомления*: '
                                                    f'{"/".join(i[2].split('.'))}\n*статус*: {i[3]}',
                                                    parse_mode="MarkdownV2")
                await update.message.reply_text('Какую из этих задач вы хотите изменить? Введите её id')
                return 3
        except Exception:
            await update.message.reply_text(
                'Вы ввели несуществующее название. Попробуйте запустить команду и ввести данные заново')
            return ConversationHandler.END
    return 2


async def second_response_del(update, context):
    if update.message.text.strip().lower() == "да":
        main1.cur.execute("DELETE FROM database where id = ?", (context.user_data['id'],))
        main1.con.commit()
        if len(TASK_NOTIFICATIONS[context.user_data['name']]) > 1:
            for i in range(len(TASK_NOTIFICATIONS[context.user_data['name']])):
                if TASK_NOTIFICATIONS[context.user_data['name']][i] == context.user_data['date']:
                    del TASK_NOTIFICATIONS[context.user_data['name']][i]
        else:
            del TASK_NOTIFICATIONS[context.user_data['name']]
        await update.message.reply_text(
            f'Задача с id={context.user_data["id"]} успешно удалена')
    context.user_data.clear()
    return ConversationHandler.END


async def third_response_del(update, context):
    context.user_data['id'] = update.message.text
    try:
        context.user_data['date'] = main1.cur.execute("SELECT * FROM database WHERE id = ?",
                                                          (context.user_data['id'],)).fetchone()[2]
        await update.message.reply_text(
            'Чтобы удалить задачу, отправьте слово "да" и она удалится.')
    except Exception:
        await update.message.reply_text(
            'Нужен существующий id из задач выше. Не испытывайте моё терпение! Введите id заново')
        return 3
    return 2


async def stop_del_task(update, context):
    await update.message.reply_text("Удаление задачи приостановлено!")
    context.user_data.clear()
    return ConversationHandler.END


async def change_task(update, context):
    await update.message.reply_text("Введите id задачи или её название:")
    return 1


async def first_response_change(update, context):
    if update.message.text.isdigit():
        context.user_data['id'] = int(update.message.text)
        try:
            res = main1.cur.execute("SELECT * FROM database WHERE id = ?", (context.user_data['id'],)).fetchone()
            await update.message.reply_text(f'*id*: {str(res[0])}\n*название*: {res[1]}\n*время уведомления*: '
                                        f'{"/".join(res[2].split('.'))}\n*статус*: {res[3]}',
                                        parse_mode="MarkdownV2")
            context.user_data['name'] = res[1]
            context.user_data['old_date'] = res[2]
            await update.message.reply_text(
                'Что хотите изменить в этой задаче? Помните, что id изменять нельзя. '
                'Введите слово: "название", "время" или "статус"')

        except Exception:
            await update.message.reply_text(
                'Вы ввели несуществующий id. Попробуйте запустить команду и ввести данные заново')
            return ConversationHandler.END
    else:
        name = update.message.text
        context.user_data['name'] = name
        try:
            res = main1.cur.execute(
                f"SELECT * FROM database where название like '%{name.lower()}%' or название like "
                f"'%{name.capitalize()}%'").fetchall()
            if len(res) == 1:
                await update.message.reply_text(f'*id*: {str(res[0])}\n*название*: {res[1]}\n*время уведомления*: '
                                            f'{"/".join(res[2].split('.'))}\n*статус*: {res[3]}',
                                            parse_mode="MarkdownV2")
                context.user_data['id'] = int(res[0])
                context.user_data['old_date'] = res[2]
                await update.message.reply_text(
                    'Что хотите изменить в этой задаче? Помните, что id изменять нельзя. '
                    'Введите слово: "название", "время" или "статус"')
            else:
                for i in res:
                    await update.message.reply_text(f'*id*: {str(i[0])}\n*название*: {i[1]}\n*время уведомления*: '
                                                    f'{"/".join(i[2].split('.'))}\n*статус*: {i[3]}',
                                                    parse_mode="MarkdownV2")
                await update.message.reply_text('Какую задачу хотите изменить? Введите её id')
                return 4
        except Exception:
            await update.message.reply_text(
                'Вы ввели несуществующее название. Попробуйте запустить команду и ввести данные заново')
            return ConversationHandler.END
    return 2


async def second_response_change(update, context):
    context.user_data['what_change'] = update.message.text.strip().lower()
    if (context.user_data['what_change'] == 'название'
            or context.user_data['what_change'] == 'время'
            or context.user_data['what_change'] == 'статус'):
        await update.message.reply_text(
            f'Введите {context.user_data['what_change'].strip()}')
        return 3
    else:
        await update.message.reply_text(
            'Проверьте корректность введенных данных. Внимательно читайте инструкции. Введите данные заново')
        return 2


async def third_response_change(update, context):
    context.user_data['new'] = update.message.text
    if context.user_data['what_change'] == 'название':
        main1.cur.execute("UPDATE database SET название = ? where id = ?",
                         (context.user_data['new'], context.user_data['id']))
        main1.con.commit()
        TASK_NOTIFICATIONS[context.user_data['new']] = TASK_NOTIFICATIONS[context.user_data['name']]
        del TASK_NOTIFICATIONS[context.user_data['name']]
    elif context.user_data['what_change'] == 'время':
        try:
            datetime.strptime(context.user_data['new'], "%d.%m.%Y %H:%M")
            main1.cur.execute("UPDATE database SET время_уведомления = ? where id = ?",
                            (context.user_data['new'], context.user_data['id']))
            main1.con.commit()
            for i in range(len(TASK_NOTIFICATIONS[context.user_data['name']])):
                if TASK_NOTIFICATIONS[context.user_data['name']][i] == context.user_data['old_date']:
                    del TASK_NOTIFICATIONS[context.user_data['name']][i]
                    TASK_NOTIFICATIONS[context.user_data['name']] += [context.user_data['new']]
        except Exception as err:
            print(err)
            await update.message.reply_text("Неверный формат даты! Используйте ДД.ММ.ГГГГ Ч:ММ")
            return 3
    elif context.user_data['what_change'] == 'статус':
        main1.cur.execute("UPDATE database SET статус = ? where id = ?",
                        (context.user_data['new'], context.user_data['id']))
        main1.con.commit()
    await update.message.reply_text("Изменения сохранены")
    context.user_data.clear()
    return ConversationHandler.END


async def stop_change(update, context):
    await update.message.reply_text("Изменение задачи приостановлено!")
    context.user_data.clear()
    return ConversationHandler.END


async def forth_response_change(update, context):
    context.user_data['id'] = update.message.text
    try:
        context.user_data['old_date'] = main1.cur.execute("SELECT * FROM database WHERE id = ?",
                                                      (context.user_data['id'],)).fetchone()[2]
        await update.message.reply_text(
            'Что хотите изменить в этой задаче? Помните, что id изменять нельзя. '
            'Введите слово: "название", "время уведомления" или "статус"')
    except Exception:
        await update.message.reply_text(
            'Нужен существующий id из задач выше. Не испытывайте моё терпение! Введите id заново')
        return 4
    return 2


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("update", update))
    application.add_handler(CommandHandler("view_all_tasks", view_all_tasks))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("view_reminders", view_reminders))

    # Обработчик для установки напоминаний
    reminder_handler = ConversationHandler(
        entry_points=[CommandHandler('set_reminder', set_reminder)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_reminder_time)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_reminder)],
        },
        fallbacks=[CommandHandler('stop_reminder', stop_reminder)]
    )
    application.add_handler(reminder_handler)

    # Оригинальные обработчики из вашего кода

    handler_change = ConversationHandler(
        entry_points=[CommandHandler('change_task', change_task)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_response_change)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, second_response_change)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, third_response_change)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, forth_response_change)]
        },
        fallbacks=[CommandHandler('stop_change', stop_change)]
    )
    application.add_handler(handler_change)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('new_task', new_task)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_response)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_status)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, write_in)]
        },
        fallbacks=[CommandHandler('stop_new_task', stop_new_task)]
    )
    application.add_handler(conv_handler)

    conv_handler_del = ConversationHandler(
        entry_points=[CommandHandler('delete_task', delete_task)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_response_del)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, second_response_del)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, third_response_del)]
        },
        fallbacks=[CommandHandler('stop_del_task', stop_del_task)]
    )
    application.add_handler(conv_handler_del)

    conv_handler_del_all = ConversationHandler(
        entry_points=[CommandHandler('delete_all_tasks', delete_all_tasks)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_all_1)]
        },
        fallbacks=[CommandHandler('stop_del_all', stop_del_all_tasks)]
    )
    application.add_handler(conv_handler_del_all)

    application.run_polling()


if __name__ == '__main__':
    main()
