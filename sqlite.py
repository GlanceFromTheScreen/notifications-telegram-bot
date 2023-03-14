import sqlite3 as sq


async def db_start():
    global db, cur

    db = sq.connect('new.db')
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users(user_id TEXT PRIMARY KEY)")
    db.commit()


async def create_user_notifications_table(user_id):
    """
    Таблица users уже создана. Если пользователь еще не добавлен в нее, то
    добавляем + создаем таблицу {user_id}_notifications - таблица его дел
    """
    user = cur.execute("SELECT 1 FROM users WHERE user_id == '{key}'".format(key=user_id)).fetchone()
    if not user:
        print(user_id)
        cur.execute("INSERT INTO users VALUES(?)", (user_id, ))
        cur.execute("CREATE TABLE '{id}_notifications'(id INTEGER PRIMARY KEY AUTOINCREMENT, is_Done INT, description TEXT, calendar TEXT, time TEXT,"
                    "user_ TEXT, FOREIGN KEY (user_) REFERENCES users(user_id) ON DELETE CASCADE)".format(id=user_id))
        db.commit()


async def add_notification_in_table(state, user_id):
    async with state.proxy() as data:
        cur.execute("INSERT INTO '{user_id}_notifications' (is_Done, description, calendar, time, user_) "
                    "VALUES(?, ?, ?, ?, ?)".format(user_id=user_id),
                    (0, data['description'], data['calendar'], data['time'], user_id,))
        db.commit()


def get_undone_tasks(user_id):
    done_tasks = cur.execute("SELECT * FROM '{user_id}_notifications' WHERE  is_Done = 0 ORDER BY calendar"
                             .format(user_id=user_id)).fetchall()
    return done_tasks


def get_done_tasks(user_id):
    done_tasks = cur.execute("SELECT * FROM '{user_id}_notifications' WHERE  is_Done = 1 ORDER BY calendar"
                             .format(user_id=user_id)).fetchall()
    return done_tasks


def get_task_by_number(user_id, number):
    notify = cur.execute("SELECT * FROM '{user_id}_notifications' WHERE id == '{number}'"
                .format(user_id=user_id, number=number)).fetchone()
    return notify


def update_notification(user_id, line):  # только line надо правильно вычислять. Может быть сортировать бд сначала
    pass

