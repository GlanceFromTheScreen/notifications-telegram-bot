from aiogram import types, executor, Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher.filters import Text
from aiogram_calendar import simple_cal_callback, SimpleCalendar
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import TOKEN_API
from sqlite import db_start, create_user_notifications_table, add_notification_in_table, get_undone_tasks,\
    get_done_tasks, get_task_by_number, update_notification_field, delete_notification_field
import datetime
from datetime import timedelta


async def on_startup(_):
    await db_start()


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


def get_main_kb() -> ReplyKeyboardMarkup:
    """
    фабрика клавиатуры главного меню
    :return:
    """
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Добавить напоминание')) \
        .add(KeyboardButton('Редактировать текущие дела')) \
        .add(KeyboardButton('Посмотреть запланированные дела')) \
        .add(KeyboardButton('Посмотреть завершенные дела')) \
        .add(KeyboardButton('/create'))

    return kb


def get_what_to_change_kb() -> ReplyKeyboardMarkup:
    """
    фабрика клавиатуры главного меню
    :return:
    """
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton('Описание'), KeyboardButton('Файлы')) \
        .add(KeyboardButton('Дата'), KeyboardButton('Время')) \
        .add(KeyboardButton('Отметить как выполненное'), KeyboardButton('Добавить / снять периодичность')) \
        .add(KeyboardButton('Удалить напоминание'), KeyboardButton('Вернуться в главное меню'))

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



#  обработчик первой команды start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message) -> None:
    await message.answer('To-Do List Application!',
                         reply_markup=get_main_kb())

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
    await NotificationStatesGroup.next()


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
    await NotificationStatesGroup.next()


#  обработчик времени
@dp.message_handler(content_types=['text'], state=NotificationStatesGroup.time)
async def load_time(message: types.Message, state: FSMContext) -> None:
    async with state.proxy() as data:
        data['time'] = message.text

    await add_notification_in_table(state, user_id=message.from_user.id)
    await message.reply('Ваша акнета успешно создана!', reply_markup=get_main_kb())
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
    await update_notification_field(state, user_id=message.from_user.id, field_data=message.text, field_name='description')
    await message.reply("Новое описание успешно сохранено",
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
        await update_notification_field(state, user_id=callback_query.from_user.id, field_data=new_date, field_name='calendar')
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
    await message.reply("Новое время успешно сохранено",
                        reply_markup=get_main_kb())
    await state.finish()


#  отмечаем как выполненное
@dp.message_handler(Text(equals="Отметить как выполненное"), state=UpdateNotificationsStateGroup.what_to_change)
async def update_is_Done(message: types.Message, state: FSMContext) -> None:
    await update_notification_field(state, user_id=message.from_user.id, field_data=1, field_name='is_Done')
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
    await callback.message.answer(f'Вы изменяете напоминание:\n{notify}\nКакую дату необходимо поставить??',
                                  reply_markup=await SimpleCalendar().start_calendar())
    await UpdateNotificationsStateGroup.calendar.set()
    await callback.answer(f'{notification_number}')


if __name__ == '__main__':
    executor.start_polling(dp,
                           skip_updates=True,
                           on_startup=on_startup)
