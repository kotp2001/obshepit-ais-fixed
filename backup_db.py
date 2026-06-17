import os
import shutil
from datetime import datetime

backup_dir = 'backups'
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

db_path = 'db.sqlite3'
if os.path.exists(db_path):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(backup_dir, f'db_backup_{timestamp}.sqlite3')
    shutil.copy2(db_path, backup_path)
    print(f'Резервная копия создана: {backup_path}')
else:
    print('База данных не найдена')
