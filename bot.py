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
    get_done_tasks, get_task_by_number


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
    kb.add(KeyboardButton('Описание')) \
        .add(KeyboardButton('Дата')) \
        .add(KeyboardButton('Время')) \
        .add(KeyboardButton('Отметить как выполненное')) \

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
                               parse_mode=types.ParseMode.HTML)


'----- Редактор напоминаний -----'


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
        await bot.send_message(message.chat.id, '<b>Какое из текущих дел вы хотите отредактировать?</b>',
                               parse_mode=types.ParseMode.HTML,
                               reply_markup=get_ikb_with_notifications(undone_tasks))


@dp.callback_query_handler()
async def callback_check_actual_tasks(callback: types.CallbackQuery):
    notification_number = callback.data  # Это номер нужной нам строки в таблице
    notify = get_task_by_number(callback.from_user.id, notification_number)
    print(notify)
    await callback.message.answer(f'Вы изменяете напоминание:\n{notify}\nЧто именно вы ходите изменить?',
                                  reply_markup=get_what_to_change_kb())
    await UpdateNotificationsStateGroup.what_to_change.set()
    await callback.answer(f'{notification_number}')


# #  обработчик команды "Добавить напонинание"
# @dp.message_handler(Text(equals="Добавить напоминание"))
# async def cmd_add_notify(message: types.Message) -> None:
#     """Обработчик сообщения Добавить напоминание"""
#     await message.reply("Введите текст напоминания",
#                         reply_markup=get_cancel_kb())
#     await NotificationStatesGroup.description.set()  # установили состояние описания


if __name__ == '__main__':
    executor.start_polling(dp,
                           skip_updates=True,
                           on_startup=on_startup)
