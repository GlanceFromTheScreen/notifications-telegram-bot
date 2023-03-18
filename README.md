Телеграм - бот, реализующий функционал to-do list приложения

Не забыть добавить config.py

Возможности:
1) Выбор даты, времени напоминания
2) Приложение к напоминанию файлов (в неограниченном количестве. Сначала один, потом - через редактор)
3) Редактор напоминания (изменение параметров)
4) Отметка напоминания как периодического (через редактор)
5) Перенесение напоминания в выполненные (через редактор)
6) Возвращение напоминания в незавершенные (через список завершенных напоминаний)
7) Удаление напоминания (через редактор) 
8) Отправка напоминания, если настали дата и время
9) Просмотр завершенных и незавершенных напоминаний

Реализация:
1) Бот: python + aiogram 2.25.1
2) Данные о напоминании (кроме файлов) хранятся в базе данных sqlite
3) Файлы хранятся в google drive 

Замечания:
1) Из-за того, что обмен данными с google api происходит не моментально (3-4 секунды), существенно замедляется работа бота. Считаю, что не очень рационально запускаемый файл и файлы напоминаний хранить в разных директориях. Оптимальнее по времени было бы хранение файлов напоминаний локально, все вместе же выгружать на сервер
2) Запрет создания напоминания с прошедшей датой
3) Удаление некоторых несущественных сообщений в диалоге с ботом с целью оптимизации и эргономики
