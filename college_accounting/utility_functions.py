import os


def delete_database(db_path: str) -> None:
    '''Deletes a SQLite database file if it exists.'''
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f'🗑️ Database deleted: {db_path}')
        except PermissionError:
            print(f'❌ Permission denied. Could not delete {db_path}')
        except Exception as e:
            print(f'❌ Failed to delete {db_path}: {e}')
    else:
        print(f'ℹ️ Database does not exist: {db_path}')
