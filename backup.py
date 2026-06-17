import os
import shutil
from datetime import datetime

def backup_database():
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    db_path = 'db.sqlite3'
    if os.path.exists(db_path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'db_backup_{timestamp}.sqlite3')
        shutil.copy2(db_path, backup_path)
        print(f'Резервная копия создана: {backup_path}')
        
        # Удаляем старые копии (старше 30 дней)
        for file in os.listdir(backup_dir):
            file_path = os.path.join(backup_dir, file)
            if os.path.getctime(file_path) < (datetime.now().timestamp() - 30 * 24 * 3600):
                os.remove(file_path)
                print(f'Удалена старая копия: {file}')
        return True
    else:
        print('База данных не найдена')
        return False

if __name__ == '__main__':
    backup_database()
