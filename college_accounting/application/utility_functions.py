import logging
import os


def delete_database(db_path: str) -> None:
    '''Deletes a SQLite database file if it exists.'''
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            logging.debug(f'🗑️ Database deleted: {db_path}')
        except PermissionError:
            logging.error(f'❌ Permission denied. Could not delete {db_path}')
        except Exception as e:
            logging.error(f'❌ Failed to delete {db_path}: {e}')
    else:
        print(f'ℹ️ Database does not exist: {db_path}')
