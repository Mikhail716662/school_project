from PyQt6 import uic
import sys
from PyQt6.QtWidgets import (QTableWidgetItem, QMainWindow, QMessageBox, QWidget, QApplication)
import main1
import webbrowser
from datetime import datetime


class MyWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('forms/main_form.ui', self)
        self.add.clicked.connect(self.add_form)
        self.delit.clicked.connect(self.delit_form)
        self.save.clicked.connect(self.change_form)
        self.update.clicked.connect(self.select_data)
        self.lineEdit.textChanged.connect(self.search)
        self.tableWidget.itemChanged.connect(self.item_changed)
        self.help.clicked.connect(self.help1)
        self.modified_column = []
        self.modified_words = []
        self.rows = []
        self.id = []
        self.select_data()

    def item_changed(self, item):
        self.modified_words += [item.text()]
        self.modified_column += [item.column()]
        self.rows += [item.row()]

    def add_form(self):
        self.add_form = AddForm()
        self.add_form.show()

    def delit_form(self):
        rows = [j + 1 for j in list(set([i.row() for i in self.tableWidget.selectedItems()]))]
        if len(rows) != 0:
            valid = QMessageBox.question(
                self, 'Подтверждение', f"Действительно удалить все элементы в рядах {rows}?",
                buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if valid == QMessageBox.StandardButton.Yes:
                for i in rows:
                    main1.cur.execute("DELETE FROM database where ID = ?", (self.id[i - 1],))
                    main1.con.commit()
                QMessageBox.information(self, "Успешно", 'Задача(-и) успешно удалена(-ы)!')
                rows.clear()
        else:
            QMessageBox.information(self, "Удалить", "Выберите задачу для удаления")

    def change_form(self):
        for i in range(len(self.modified_column)):
            if self.modified_column[i] == 1:
                if self.modified_words[i] == '' or self.modified_words[i].isspace():
                    QMessageBox.critical(self, 'Ошибка', "Новые названия задач не могут быть пустыми!\n"
                                                         "Пожалуйста, повторите все изменения")
                    self.select_data()
                    break
                main1.cur.execute("UPDATE database SET название = ? where id = ?",
                                 (self.modified_words[i], self.id[self.rows[i]]))
                main1.con.commit()
            elif self.modified_column[i] == 2:
                try:
                    datetime.strptime(self.modified_words[i], "%d.%m.%Y %H:%M")
                    main1.cur.execute("UPDATE database SET время_уведомления = ? where id = ?",
                                      (self.modified_words[i], self.id[self.rows[i]]))
                    main1.con.commit()
                except Exception:
                    QMessageBox.critical(self, 'Ошибка', "Неверный формат даты! "
                                                         "Используйте ДД.ММ.ГГГГ Ч:ММ")
                    self.select_data()
                    break
            elif self.modified_column[i] == 3:
                if self.modified_words[i] == '' or self.modified_words[i].isspace():
                    QMessageBox.critical(self, 'Ошибка', "Новый статус задач не может быть пустым!\n"
                                                         "Пожалуйста, повторите все изменения")
                    self.select_data()
                    break
                main1.cur.execute("UPDATE database SET статус = ? where id = ?",
                                 (self.modified_words[i], self.id[self.rows[i]]))
                main1.con.commit()
        else:
            QMessageBox.information(self, "Успешно", 'Изменения сохранены успешно!')

    def search(self):
        search_text = self.lineEdit.text()

        # Очищаем результаты поиска
        self.tableWidget.setRowCount(0)
        # Выполняем поиск похожих компонентов
        res = main1.cur.execute(f"SELECT * FROM database where название like '%{search_text.lower()}%' or название like "
                               f"'%{search_text.capitalize()}%'").fetchall()
        self.id = [i[0] for i in res]
        for i, row in enumerate(res):
            self.tableWidget.setRowCount(
                self.tableWidget.rowCount() + 1)
            for j, elem in enumerate(row):
                self.tableWidget.setItem(
                    i, j, QTableWidgetItem(str(elem)))
        self.modified_words = []
        self.modified_column = []
        self.rows = []

    def select_data(self):
        self.lineEdit.clear()
        res = main1.cur.execute("SELECT * FROM database").fetchall()
        self.id = [i[0] for i in res]
        self.tableWidget.setColumnCount(4)
        self.tableWidget.setRowCount(0)
        self.tableWidget.setHorizontalHeaderLabels(['ID', 'Название', 'Время уведомления', 'Статус'])
        for i, row in enumerate(res):
            self.tableWidget.setRowCount(
                self.tableWidget.rowCount() + 1)
            for j, elem in enumerate(row):
                self.tableWidget.setItem(
                    i, j, QTableWidgetItem(str(elem)))
        self.modified_words = []
        self.modified_column = []
        self.rows = []

    def help1(self):
        webbrowser.open("https://disk.yandex.ru/i/3v5b1COxH9SDtA")


class AddForm(QWidget):
    def __init__(self):
        super().__init__()
        uic.loadUi('forms/new_task.ui', self)
        self.back.clicked.connect(self.backy)
        self.save.clicked.connect(self.save_all)

    def save_all(self):
        name = self.name.text()
        if name == '' or name.isspace():
            QMessageBox.critical(self, 'Ошибка', "Название задачи не может быть пустым!")
        else:
            date_time = self.dateTime.text()
            if name == '' or name.isspace():
                QMessageBox.critical(self, 'Ошибка', "Новые названия задач не могут быть пустыми!\n"
                                                     "Пожалуйста, повторите все изменения")
            try:
                datetime.strptime(date_time, "%d.%m.%Y %H:%M")
                main1.cur.execute("""
                    INSERT INTO database (название, время_уведомления, статус)
                    VALUES (?, ?, ?)
                """, (name, date_time, 'Не выполнено'))
                main1.con.commit()
                QMessageBox.information(self, "Успешно", 'Задача успешно добавлена!')
            except Exception as err:
                QMessageBox.critical(self, 'Ошибка', "Неверный формат даты! Используйте ДД.ММ.ГГГГ Ч:ММ")
                print(err)
                return False

    def backy(self):
        AddForm.close(self)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyWidget()
    ex.show()
    sys.exit(app.exec())