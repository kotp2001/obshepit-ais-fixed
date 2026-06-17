import os
import sqlite3
import base64

db_path = 'db.sqlite3'

if os.path.exists(db_path):
    with open(db_path, 'rb') as f:
        data = base64.b64encode(f.read()).decode('utf-8')
        print('=== START_DB_BASE64 ===')
        print(data)
        print('=== END_DB_BASE64 ===')
else:
    print('Файл базы данных не найден')
