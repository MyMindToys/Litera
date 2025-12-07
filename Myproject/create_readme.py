# -*- coding: utf-8 -*-
content = """Заменить: templates
Заменить: db.sqlite3

Комментарий к коммиту: Добавление кнопки Просмотр в таблице Список проверок для перехода на страницу с распарсенным текстом
"""
with open('../temp_patch/README_PATCH.txt', 'w', encoding='utf-8') as f:
    f.write(content)


