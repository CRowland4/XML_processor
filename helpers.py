import os  # built-in library


GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
DEFAULT_COLOR = '\033[0m'


def is_valid_xml(file_path) -> bool:
    """Performs three checks: File is accessible, file is an xml file, and xml is valid."""
    if not file_path.endswith('.xml'):
        print(f'{YELLOW}The file extension must be ".xml".{DEFAULT_COLOR}\n')
        return False
    if not os.path.exists(file_path):
        print(f'{YELLOW}This file is not in the working directory.{DEFAULT_COLOR}\n')
        return False
    return True


def is_valid_db(db_name):
    if not db_name.endswith('.db'):
        print(f'{YELLOW}The file extension must be ".db"{DEFAULT_COLOR}\n')
        return False
    if not os.path.exists(db_name):
        print(f'{GREEN}Creating new database: {db_name}{DEFAULT_COLOR}\n')
        return True
    else:
        print(f'{GREEN}Connecting to existing database: {db_name}{DEFAULT_COLOR}\n')
        return True


