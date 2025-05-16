import sqlite3

# Подключение к БД
con = sqlite3.connect("db/database.db")

# Создание курсора
cur = con.cursor()