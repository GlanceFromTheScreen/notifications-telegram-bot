from aiogram import types, executor, Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.filters import Text
from aiogram_calendar import simple_cal_callback, SimpleCalendar
from aiogram.types import Message, CallbackQuery, InputFile
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import TOKEN_API
from sqlite import db_start, create_user_notifications_table, add_notification_in_table, get_undone_tasks, \
    get_done_tasks, get_task_by_number, update_notification_field, delete_notification_field, get_used_ids, \
    update_notification_field_by_number, get_unsent_tasks, get_last_notification
import datetime
from datetime import timedelta
import aioschedule
import asyncio

from google_drive import create_folder_in_folder, is_directory_or_file_exists, upload_file, get_list_of_files, \
    delete_files_from_google_disk

import os



async def scheduler():
    aioschedule.every(0.05).minutes.do(notification_function)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(0.05)


def add_days(date, add_type):
    date0 = datetime.datetime.strptime(str(date), "%d/%m/%Y").date()
    if add_type == 1:
        date = date0 + timedelta(days=1)
    if add_type == 2:
        date = date0 + timedelta(days=7)
    if add_type == 3:
        date = date0 + timedelta(days=30)

    date = str(date)
    if '-' in date:
        date = date.replace('-', '/')
        date = date.split('/')
        date.reverse()
        date = '/'.join(date)
        date = str(date)

    return date


def check_for_notification(date, project_time):
    if date:
        if '-' in date:
            date = date.replace('-', '/')
            date = date.split('/')
            date.reverse()
            date = '/'.join(date)
            date = str(date)

        d1 = datetime.datetime.strptime(date, "%d/%m/%Y").date()
        d2 = datetime.datetime.now().date()

        t1 = datetime.datetime.strptime(project_time, '%H:%M').time()

        current_date_time = datetime.datetime.now()
        t2 = current_date_time.time()

        if d2 >= d1 and t2 >= t1:
            return True
        else:
            return False


async def on_startup(_):
    await db_start()
    asyncio.create_task(scheduler())


storage = MemoryStorage()
bot = Bot(TOKEN_API)
dp = Dispatcher(bot,
                storage=storage)


class NotificationStatesGroup(StatesGroup):
    """машина конечных состояний бота"""
    description = State()
    calendar = State()
    time = State()
    file = State()


class UpdateNotificationsStateGroup(StatesGroup):
    actual_tasks = State()
    done_tasks = State()
    what_to_change = State()
    description = State()
    calendar = State()
    time = State()
    file = State()
    periodic = State()


def get_main_kb() -> ReplyKeyboardMarkup:
    """
    фабрика клавиатуры главного меню
    :return:
    """
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Добавить напоминание'), KeyboardButton('Редактировать текущие дела')) \
        .add(KeyboardButton('Посмотреть запланированные дела'), KeyboardButton('Посмотреть завершенные дела'))
    return kb


def get_file_kb() -> ReplyKeyboardMarkup:
    """
    фабрика клавиатуры главного меню
    :return:
    """
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Файлы не требуются'))

    return kb


def get_what_to_change_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Описание'), KeyboardButton('Файлы')) \
        .add(KeyboardButton('Дата'), KeyboardButton('Время')) \
        .add(KeyboardButton('Отметить как выполненное'), KeyboardButton('Изменить периодичность')) \
        .add(KeyboardButton('Удалить напоминание'), KeyboardButton('Вернуться в главное меню'))

    return kb


def get_files_update_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Добавить новый'), KeyboardButton('Удалить имеющийся')) \
        .add(KeyboardButton('Вернуться в главное меню'))

    return kb


def get_done_tasks_kb() -> ReplyKeyboardMarkup:
    """
    фабрика клавиатуры главного меню
    :return:
    """
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Вернуть дело в незавершенное'), KeyboardButton('Вернуться в главное меню'))

    return kb


def get_cancel_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('/cancel'))

    return kb


def get_ikb_with_notifications(list_of_notifications: list) -> InlineKeyboardMarkup:
    ikb = InlineKeyboardMarkup(row_width=2)
    for i in range(len(list_of_notifications)):
        noty = list_of_notifications[i][1] + list_of_notifications[i][2] + list_of_notifications[i][3]
        ikb.add(InlineKeyboardButton(text=f'{noty}',
                                     callback_data=f'{list_of_notifications[i][0]}'))
    return ikb


def get_ikb_with_filenames(list_of_files: list) -> InlineKeyboardMarkup:
    ikb = InlineKeyboardMarkup(row_width=2)
    for i in range(len(list_of_files)):
        ikb.add(InlineKeyboardButton(text=f'{list_of_files[i]}',
                                     callback_data=f'{list_of_files[i]}'))
    return ikb


#  обработчик первой команды start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message) -> None:
    await message.answer('To-Do List Application!',
                         reply_markup=get_main_kb())

    # #  выгружаем файлы
    # titles = get_list_of_files('497684582', '13')
    # # await bot.send_document(message.from_user.id, f'files/{message.from_user.id}/mish.png')
    # # await message.answer_document(open(f'files/{message.from_user.id}/mish.png', "RB"))
    # await message.answer_document(InputFile(f'files/{message.from_user.id}/{titles[0]}'))

    await create_user_notifications_table(user_id=message.from_user.id)  # см. sqlite - file


#  обработчик команды cancel
@dp.message_handler(commands=['cancel'], state='*')
async def cmd_cancel(message: types.Message, state: FSMContext):
    if state is None:
        return

    await state.finish()
    await message.reply('Вы прервали создание анкеты!',
                        reply_markup=get_main_kb())


"""-----ветка про добавление напоминания-----"""


#  обработчик команды "Добавить напонинание"
@dp.message_handler(Text(equals="Добавить напоминание"))
async def cmd_add_notify(message: types.Message) -> None:
    """Обработчик сообщения Добавить напоминание"""
    await message.reply("Введите текст напоминания",
                        reply_markup=get_cancel_kb())
    await NotificationStatesGroup.description.set()  # установили состояние описания


#  обработчик введенного описания
@dp.message_handler(content_types=['text'], state=NotificationStatesGroup.description)
async def load_description(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        data['description'] = message.text

    await message.answer("Теперь выберите дату: ",
                         reply_markup=await SimpleCalendar().start_calendar())
    await NotificationStatesGroup.calendar.set()


# обработчик календаря (callback!)
@dp.callback_query_handler(simple_cal_callback.filter(), state=NotificationStatesGroup.calendar)
async def load_calendar(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    async with state.proxy() as data_dict:
        data_dict['calendar'] = date.strftime("%d/%m/%Y")
    if selected:
        await callback_query.message.answer(
            f'Вы выбрали дату: {date.strftime("%d/%m/%Y")} \n Теперь введите время',
            reply_markup=get_cancel_kb()
        )
    await NotificationStatesGroup.time.set()


#  обработчик времени
@dp.message_handler(content_types=['text'], state=NotificationStatesGroup.time)
async def load_time(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        data['time'] = message.text

    #  добавляем запись в таблицу на этом этапе! Тогда устанавливается и номер в бд
    await add_notification_in_table(state, user_id=message.from_user.id)
    # await message.reply('Напоминание слоздано!', reply_markup=get_main_kb())
    # await state.finish()
    await message.reply('Время зафиксировано! Теперь добавьте файлы', reply_markup=get_file_kb())
    await NotificationStatesGroup.file.set()


#  обработчик отсутствия файлов
@dp.message_handler(Text(equals="Файлы не требуются"), state=NotificationStatesGroup.file)
async def load_no_file(message: types.Message, state: FSMContext) -> None:
    # await add_notification_in_table(state, user_id=message.from_user.id)  # это здесь уже не нужно, получается
    await message.reply('Напоминание слоздано!', reply_markup=get_main_kb())
    await state.finish()


# обработчик файлов: загрузка их сначала в локальную директорию
'''
1) файл добавляется в локальную директорию в папку files/id
2) напоминание только создается, пожтому надо создать дир. на диске: files/id/notification_id
3) добавляем в нее файл
'''
@dp.message_handler(content_types=types.ContentTypes.DOCUMENT, state=NotificationStatesGroup.file)
async def load_file(message: types.Message, state: FSMContext) -> None:
    if document := message.document:
        await document.download(
            # destination_dir=f"files/{message.from_user.id}",
            destination_file=f"files/{message.from_user.id}/{document.file_name}",
        )

    await bot.send_message(chat_id=message.from_user.id,
                           text='Загружаю файл...')

    #  если еще ни разу не добавлялиь файлы, то создаем папку с id пользователя
    if not is_directory_or_file_exists('files', f'{message.from_user.id}'):
        create_folder_in_folder('files', f'{message.from_user.id}')

    #  создаем папку с id НАПОМИНАНМЯ!
    this_notify = get_last_notification(message.from_user.id)
    create_folder_in_folder(f'{message.from_user.id}', f'{this_notify[0]}')

    if not is_directory_or_file_exists(f'{this_notify[0]}', f'{document.file_name}'):
        # upload_file(f'{document.file_name}', f'files/{message.from_user.id}/{this_notify[0]}')
        upload_file(f'{message.from_user.id}', f'{this_notify[0]}', f'files/{message.from_user.id}/{document.file_name}', f'{document.file_name}')

    #  удаляем файлы из локальной директории
    os.remove(f'files/{message.from_user.id}/{document.file_name}')

    await bot.send_message(chat_id=message.from_user.id,
                           text='Успешно! Файл загружен',
                           reply_markup=get_main_kb())
    await state.finish()


"""----- Просмотр списков напоминаний -----"""


@dp.message_handler(Text(equals="Посмотреть запланированные дела"))
async def check_actual_tasks(message: types.Message) -> None:
    undone_tasks = ""
    tasks = get_undone_tasks(message.from_user.id)
    num = 1
    for task in tasks:
        undone_tasks += f"<b>{num}. {task[2]}</b> - <b>{task[3]}</b>\n {task[4]}\n"
        num = num + 1
    if num == 1:
        await bot.send_message(message.chat.id, 'Список текущих дел пуст')
    else:
        await bot.send_message(message.chat.id, '<b>Ваши текущие дела:</b>\n\n' + undone_tasks,
                               parse_mode=types.ParseMode.HTML)


@dp.message_handler(Text(equals="Посмотреть завершенные дела"))
async def check_actual_tasks(message: types.Message) -> None:
    done_tasks = ""
    tasks = get_done_tasks(message.from_user.id)
    num = 1
    for task in tasks:
        done_tasks += f"<b>{num}. {task[2]}</b> - <b>{task[3]}</b>\n {task[4]}\n"
        num = num + 1
    if num == 1:
        await bot.send_message(message.chat.id, 'Список выполненных дел пуст')
    else:
        await bot.send_message(message.chat.id, '<b>Ваши завершенные дела:</b>\n\n' + done_tasks,
                               parse_mode=types.ParseMode.HTML, reply_markup=get_done_tasks_kb())


'----- Редактор текущих напоминаний -----'


@dp.message_handler(Text(equals="Редактировать текущие дела"))
async def check_actual_tasks(message: types.Message) -> None:
    undone_tasks = []
    tasks = get_undone_tasks(message.from_user.id)
    num = 1
    for task in tasks:
        undone_tasks.append([f"{task[0]}", f"{task[3]}, ", f"{task[4]}, ", f"{task[2]}"])
        num = num + 1
    if num == 1:
        await bot.send_message(message.chat.id, 'Список текущих дел пуст')
    else:
        await UpdateNotificationsStateGroup.actual_tasks.set()
        await bot.send_message(message.chat.id, '<b>Какое из текущих дел вы хотите отредактировать?</b>',
                               parse_mode=types.ParseMode.HTML,
                               reply_markup=get_ikb_with_notifications(undone_tasks))


@dp.callback_query_handler(state=UpdateNotificationsStateGroup.actual_tasks)
async def callback_check_actual_tasks(callback: types.CallbackQuery, state: FSMContext):
    notification_number = callback.data  # Это номер нужной нам строки в таблице
    notify = get_task_by_number(callback.from_user.id, notification_number)
    #  записываем номер выбранного пользователем сообщение (номер = id в бд)
    async with state.proxy() as data:
        data['notification_number'] = notification_number

    await callback.message.answer(f'Вы изменяете напоминание:\n{notify}\nЧто именно вы ходите изменить?',
                                  reply_markup=get_what_to_change_kb())
    await UpdateNotificationsStateGroup.what_to_change.set()
    await callback.answer(f'{notification_number}')


#  возвращаемся в главное меню
@dp.message_handler(Text(equals="Вернуться в главное меню"), state='*')
async def back_to_main_menu(message: types.Message, state: FSMContext) -> None:
    await message.reply("Вы вернулись в главное меню",
                        reply_markup=get_main_kb())
    await state.finish()


#  обновляем описание
@dp.message_handler(Text(equals="Описание"), state=UpdateNotificationsStateGroup.what_to_change)
async def update_description(message: types.Message) -> None:
    await message.reply("Введите новое описание для нопоминания",
                        reply_markup=get_cancel_kb())
    await UpdateNotificationsStateGroup.description.set()  # установили состояние описания


@dp.message_handler(content_types=['text'], state=UpdateNotificationsStateGroup.description)
async def save_update_description(message: types.Message, state: FSMContext) -> None:
    await update_notification_field(state, user_id=message.from_user.id, field_data=message.text,
                                    field_name='description')
    #  после обновления напоминания его надо будет отправить еще раз
    await update_notification_field(state, user_id=message.from_user.id, field_data=0, field_name='is_Sent')
    await message.reply("Новое описание успешно сохранено",
                        reply_markup=get_main_kb())
    await state.finish()


#  обновляем периодичность
@dp.message_handler(Text(equals="Изменить периодичность"), state=UpdateNotificationsStateGroup.what_to_change)
async def update_periodic(message: types.Message) -> None:
    await message.reply("Введите тип периодичности",
                        reply_markup=get_cancel_kb())
    await UpdateNotificationsStateGroup.periodic.set()  # установили состояние описания


@dp.message_handler(content_types=['text'], state=UpdateNotificationsStateGroup.periodic)
async def save_update_periodic(message: types.Message, state: FSMContext) -> None:
    await update_notification_field(state, user_id=message.from_user.id, field_data=int(message.text),
                                    field_name='period_type')
    #  после обновления напоминания его надо будет отправить еще раз
    await update_notification_field(state, user_id=message.from_user.id, field_data=0, field_name='is_Sent')
    await message.reply("Периодичность обновлена",
                        reply_markup=get_main_kb())
    await state.finish()


#  обновляем календарную дату
@dp.message_handler(Text(equals="Дата"), state=UpdateNotificationsStateGroup.what_to_change)
async def update_description(message: types.Message) -> None:
    await message.reply("Введите новую дату для нопоминания",
                        reply_markup=await SimpleCalendar().start_calendar())
    await UpdateNotificationsStateGroup.calendar.set()  # установили состояние описания


#  callback календаря!
@dp.callback_query_handler(simple_cal_callback.filter(), state=UpdateNotificationsStateGroup.calendar)
async def save_update_calendar(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback_query, callback_data)
    new_date = date.strftime("%d/%m/%Y")
    if selected:
        await update_notification_field(state, user_id=callback_query.from_user.id, field_data=new_date,
                                        field_name='calendar')
        #  после обновления напоминания его надо будет отправить еще раз
        await update_notification_field(state, user_id=callback_query.from_user.id, field_data=0, field_name='is_Sent')
        await callback_query.message.answer(
            f'Вы изменили дату: {date.strftime("%d/%m/%Y")}',
            reply_markup=get_main_kb()
        )
    await state.finish()


#  обновляем время
@dp.message_handler(Text(equals="Время"), state=UpdateNotificationsStateGroup.what_to_change)
async def update_time(message: types.Message) -> None:
    await message.reply("Введите новое время для нопоминания",
                        reply_markup=get_cancel_kb())
    await UpdateNotificationsStateGroup.time.set()  # установили состояние описания


@dp.message_handler(content_types=['text'], state=UpdateNotificationsStateGroup.time)
async def save_update_time(message: types.Message, state: FSMContext) -> None:
    await update_notification_field(state, user_id=message.from_user.id, field_data=message.text, field_name='time')
    #  после обновления напоминания его надо будет отправить еще раз
    await update_notification_field(state, user_id=message.from_user.id, field_data=0, field_name='is_Sent')
    await message.reply("Новое время успешно сохранено",
                        reply_markup=get_main_kb())
    await state.finish()


#  отмечаем как выполненное
@dp.message_handler(Text(equals="Отметить как выполненное"), state=UpdateNotificationsStateGroup.what_to_change)
async def update_is_Done(message: types.Message, state: FSMContext) -> None:
    await update_notification_field(state, user_id=message.from_user.id, field_data=1, field_name='is_Done')
    #  сделанные дела, даже если их время и не пришло, отправлять уже не нужно
    await update_notification_field(state, user_id=message.from_user.id, field_data=1, field_name='is_Sent')
    await message.reply("Задача выполнена",
                        reply_markup=get_main_kb())
    await state.finish()


#  удаляем напоминание
@dp.message_handler(Text(equals="Удалить напоминание"), state=UpdateNotificationsStateGroup.what_to_change)
async def back_to_main_menu(message: types.Message, state: FSMContext) -> None:
    await delete_notification_field(state, user_id=message.from_user.id)
    await message.reply("Вы удалили напоминание",
                        reply_markup=get_main_kb())
    await state.finish()


#  редактор файлов
@dp.message_handler(Text(equals="Файлы"), state=UpdateNotificationsStateGroup.what_to_change)
async def update_files(message: types.Message) -> None:
    await message.reply("Что вы хотеите сделать с файлами?",
                        reply_markup=get_files_update_kb())
    await UpdateNotificationsStateGroup.file.set()


@dp.message_handler(Text(equals="Добавить новый"), state=UpdateNotificationsStateGroup.file)
async def update_files_new(message: types.Message) -> None:
    await message.reply("Добавьте файл",
                        reply_markup=get_main_kb())
    await UpdateNotificationsStateGroup.file.set()


@dp.message_handler(content_types=types.ContentTypes.DOCUMENT, state=UpdateNotificationsStateGroup.file)
async def update_files_new(message: types.Message, state: FSMContext) -> None:
    """
    Тут код почти полностью повторяет код другой функции. Это надо по-хорошему потому убрать
    """
    if document := message.document:
        await document.download(
            destination_file=f"files/{message.from_user.id}/{document.file_name}",
        )

    await bot.send_message(chat_id=message.from_user.id,
                           text='Загружаю файл...')

    #  если еще ни разу не добавлялиь файлы, то создаем папку с id пользователя
    if not is_directory_or_file_exists('files', f'{message.from_user.id}'):
        create_folder_in_folder('files', f'{message.from_user.id}')

    async with state.proxy() as data:
        notification_number = data['notification_number']

    if not is_directory_or_file_exists(f'{message.from_user.id}', f'{notification_number}'):
        create_folder_in_folder(f'{message.from_user.id}', f'{notification_number}')

    if not is_directory_or_file_exists(f'{notification_number}', f'{document.file_name}'):
        upload_file(f'{message.from_user.id}', f'{notification_number}',
                    f'files/{message.from_user.id}/{document.file_name}', f'{document.file_name}')

    #  удаляем файлы из локальной директории
    os.remove(f'files/{message.from_user.id}/{document.file_name}')

    await bot.send_message(chat_id=message.from_user.id,
                           text='Успешно! Файл загружен',
                           reply_markup=get_main_kb())
    await state.finish()


@dp.message_handler(Text(equals="Удалить имеющийся"), state=UpdateNotificationsStateGroup.file)
async def update_files_delete(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        notification_number = data['notification_number']
    await bot.send_message(message.from_user.id, 'Секунду, подгружаем файлы...')
    list_of_files = get_list_of_files(message.from_user.id, notification_number)
    await message.reply("Выберите, какой файл вы хотите удалить",
                        reply_markup=get_ikb_with_filenames(list_of_files))
    await UpdateNotificationsStateGroup.file.set()


@dp.callback_query_handler(state=UpdateNotificationsStateGroup.file)
async def delete_files_from_disk(callback: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        notification_number = data['notification_number']
    await bot.send_message(chat_id=callback.from_user.id, text='Удаляем файл...')
    delete_files_from_google_disk(f'{callback.from_user.id}', f'{notification_number}', f'{callback.data}')
    await bot.send_message(chat_id=callback.from_user.id, text='Файл успено удалён!', reply_markup=get_main_kb())
    await state.finish()


'''----- Редактор завершенных напоминаний-----'''


@dp.message_handler(Text(equals="Вернуть дело в незавершенное"))
async def check_done_tasks(message: types.Message) -> None:
    done_tasks = []
    tasks = get_done_tasks(message.from_user.id)
    num = 1
    for task in tasks:
        done_tasks.append([f"{task[0]}", f"{task[3]}, ", f"{task[4]}, ", f"{task[2]}"])
        num = num + 1
    if num == 1:
        await bot.send_message(message.chat.id, 'Список выполненных дел пуст')
    else:
        await bot.send_message(message.chat.id, '<b>Какое из выполненных дел вы хотите вернуть?</b>',
                               parse_mode=types.ParseMode.HTML,
                               reply_markup=get_ikb_with_notifications(done_tasks))
    await UpdateNotificationsStateGroup.done_tasks.set()


@dp.callback_query_handler(state=UpdateNotificationsStateGroup.done_tasks)
async def callback_check_done_tasks(callback: types.CallbackQuery, state: FSMContext):
    notification_number = callback.data  # Это номер нужной нам строки в таблице
    notify = get_task_by_number(callback.from_user.id, notification_number)
    #  записываем номер выбранного пользователем сообщение (номер = id в бд)
    async with state.proxy() as data:
        data['notification_number'] = notification_number
    await update_notification_field(state, user_id=callback.from_user.id, field_data=0, field_name='is_Done')
    #  вернули дело в невыполненные => его еще предстоит отправить
    await update_notification_field(state, user_id=callback.from_user.id, field_data=0, field_name='is_Sent')
    await callback.message.answer(f'Вы изменяете напоминание:\n{notify}\nКакую дату необходимо поставить??',
                                  reply_markup=await SimpleCalendar().start_calendar())
    await UpdateNotificationsStateGroup.calendar.set()
    await callback.answer(f'{notification_number}')


'''----- Отправка уведомлений о заплпнированных делах -----'''


@dp.message_handler()
async def notification_function():
    # выгружаем все задания, которые находятся в статусе "текущие"
    users = get_used_ids()
    for user_id in users:
        tasks = get_unsent_tasks(user_id)
        for task in tasks:
            # проверяем не наступила ли дата и время уведомления.
            if check_for_notification(task[3], task[4]):
                # если наступило - отправляем уведомление
                #  выгружаем файлы
                titles = get_list_of_files(f'{user_id}', f'{task[0]}')

                await bot.send_message(chat_id=user_id, text=f"У вас запланировано важное дело - {task[2]}")

                for i in range(len(titles)):
                    await bot.send_document(user_id, (f'{titles[i]}', f'files/{user_id}/{titles[i]}'))
                    os.remove(f'files/{user_id}/{titles[i]}')  # удаляем из локальной директории

                # флажок, проверка на "периодичность дела"
                if task[6] == 0:
                    # если дело не переодическое то заменяем стус "в ожидании" на "отправлено"
                    await update_notification_field_by_number(number=task[0], user_id=user_id, field_data=1,
                                                              field_name='is_Sent')
                else:
                    # вычисляем новую дату для уведомления у периодических дел
                    # date_culc = select_date_task_for_periodic(task[0], task[1])
                    new_date = add_days(task[3], task[6])
                    await update_notification_field_by_number(number=task[0], user_id=user_id, field_data=new_date,
                                                              field_name='calendar')
                    # #обнавляем дату периодического дела
                    # await update_date_task_for_pereodic(task[0], task[1], res_date)


if __name__ == '__main__':
    executor.start_polling(dp,
                           skip_updates=True,
                           on_startup=on_startup)
