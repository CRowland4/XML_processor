import helpers
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ElementTree
import sqlite3  # built-in library
import sys  # built-in library


class XMLParser:
    def __init__(self):
        self.connection = None  # Sqlite3 Connection object
        self.cursor = None  # Sqlite3 Cursor object

        # If an error occurs when attempting to add an integer number to an SQL table somewhere, a negative number will
        #       be inserted instead. This will be incremented down by 1 every time it is used.
        self.error_num = -1
        self.entry = 0

        self.working_file = None
        self.file_content = None
        self.soup = None

        self.jobs = []  # Job tags from current file
        self.plans = []  # Plan tags from current file

        self.current_object_type = None
        #  Children of Job and Plan tags
        self.Name = None
        self.Description = None
        self.ID = None
        self.Enabled = None
        self.Command = None
        self.TriggerRules = None
        self.ParentObject = None
        self.Triggers = None
        self.Dependencies = None
        self.OnError = None

    def main(self):
        self.set_connection()
        self.set_cursor()

        while True:
            self.set_working_file()

            if not self.xml_is_well_formed():
                continue

            if not self.continue_table_creation():  # Checks for pre-existing table from current file
                continue

            self.set_file_content()
            self.set_soup()
            self.reset_xml_tag_attributes()
            self.set_jobs()
            self.set_plans()

            self.create_table()

            self.current_object_type = 'Plan'
            self.insert_plan_rows()

            self.current_object_type = 'Job'
            self.insert_job_rows()

            print(f'{helpers.GREEN}File processed.{helpers.DEFAULT_COLOR}\n')

        return

    def set_connection(self):
        """Connects the connection attribute with a database via user input."""
        while True:
            database_name = input("Enter the name (with .db extension) of a new or existing database: ")
            if helpers.is_valid_db(database_name):
                self.connection = sqlite3.connect(database_name)
                return
            else:
                continue

    def set_cursor(self):
        """Sets the curser attribute via the connection attribute."""
        self.cursor = self.connection.cursor()
        return

    def set_working_file(self):
        """Sets the working_file attribute via user input."""
        while True:
            file_name = input("Enter the name of your xml file (with extension), or 'q' to quit: ")

            if file_name == 'q':
                sys.exit()

            if helpers.is_valid_xml(file_name):
                self.working_file = file_name
                return
            else:
                continue

    def xml_is_well_formed(self):
        """Checks that the working_file is a well-formed xml file. """
        with open(self.working_file, 'r') as file:
            try:
                xml = file.read()
                ElementTree.fromstring(xml)
                return True
            except ElementTree.ParseError as error_message:
                print(f'Error reading file: {self.working_file}.')
                print(f'{helpers.RED}{error_message}{helpers.DEFAULT_COLOR}')
                print("Verify structure of this document or choose a new file.\n")
                return False

    def set_file_content(self):
        """Reads the working_file into the file_content attribute."""
        with open(self.working_file, 'r') as file:
            self.file_content = file.read().replace('\n', '').replace('\t', '')
        return

    def set_soup(self):
        """Sets the soup attribute from the file_content attribute."""
        self.soup = BeautifulSoup(self.file_content, 'xml')
        return

    def reset_xml_tag_attributes(self):
        """Resets the attributes containing the Job or Plan data back to None."""
        self.entry = 0
        self.current_object_type = None
        self.Name = None
        self.Description = None
        self.ID = None
        self.Enabled = None
        self.Command = None
        self.ParentObject = None
        self.TriggerRules = None
        self.Triggers = None
        self.Dependencies = None
        self.OnError = None
        return

    def set_jobs(self):
        """Adds all Job objects from the current working file into the jobs attribute."""
        self.jobs = self.soup.find_all('Job')
        return

    def set_plans(self):
        """Adds all Plan objects from the current working file into the plans attribute."""
        self.plans = self.soup.find_all('Plan')
        return

    def continue_table_creation(self):
        """Checks if a table has been created (in the connected database) from the current working file.
        If the table already exists, gives the user the option to override that table or skip this table creation."""
        table = self.cursor.execute(
            f'SELECT tbl_name FROM sqlite_master WHERE type="table" AND tbl_name="{self.working_file[:-4]}"'
        ).fetchall()

        if not table:
            return True

        override = input(f"A table already exists for {self.working_file} current file. Override this table? (y/n): ")
        if override == 'y':
            print("Overriding table\n")
            self.cursor.execute(f'DROP TABLE {self.working_file[:-4]};')
            self.connection.commit()
            return True
        else:
            print("Cancelling table creation.\n")
            return False

    def create_table(self):
        """Creates a table (with same name as current working file) for storage of data from current working file."""
        self.cursor.execute(
            f'''CREATE TABLE {self.working_file[:-4]} (
                Entry INTEGER PRIMARY KEY,
                ObjectType TEXT,
                Name TEXT,
                Description TEXT,
                ID INTEGER UNIQUE,
                Enabled INTEGER,
                Command TEXT,
                ParentObject INTEGER,
                TriggerRules TEXT,
                Triggers TEXT,
                Dependencies TEXT,
                OnError TEXT
            );'''
        )
        self.connection.commit()
        return

    def insert_job_rows(self):
        """Reads the Job data for each Job in the file_content attribute into a new row in the appropriate table."""
        for job in self.jobs:
            root = ElementTree.fromstring(str(job))
            self.cursor.execute(
                f'INSERT INTO {self.working_file[:-4]} (ObjectType) Values (?)', (self.current_object_type, )
            )
            self.entry += 1

            for element in root:
                try:
                    text_list = list(element.itertext())
                    setter = getattr(self, f'set_{element.tag.lower()}')
                    updater = getattr(self, f'update_{element.tag.lower()}')
                    setter(text_list)  # Setters note: text_list is a list object; accounts for possible child elements
                    updater(self.entry)
                except AttributeError:
                    reset = helpers.DEFAULT_COLOR
                    print(f'{helpers.YELLOW}There is an unexpected child tag in this job: <{element.tag}>.{reset}')
                    print("Please verify that the source XML document is valid and follows the desired schema.")
                    keep_going = input('Enter "c" to continue (this may cause an error), or <Enter> to quit.\n>>> ')

                    if keep_going == 'c':
                        continue
                    else:
                        sys.exit()

            self.connection.commit()

    def insert_plan_rows(self):
        """Reads Plan data for each Plan in the file_content attribute into a new row in the appropriate table."""
        for plan in self.plans:
            root = ElementTree.fromstring(str(plan))
            self.cursor.execute(
                f'INSERT INTO {self.working_file[:-4]} (ObjectType) Values (?)', (self.current_object_type, )
            )
            self.entry += 1

            for element in root:
                try:
                    text_list = list(element.itertext())
                    setter = getattr(self, f'set_{element.tag.lower()}')
                    updater = getattr(self, f'update_{element.tag.lower()}')
                    setter(text_list)  # Setters note: text_list is a list object; accounts for possible child elements
                    updater(self.entry)
                except AttributeError:
                    reset = helpers.DEFAULT_COLOR
                    print(f'{helpers.YELLOW}There is an unexpected child tag in this plan: <{element.tag}>.{reset}')
                    print("Please verify that the source XML document is valid and follows the desired schema.")
                    keep_going = input('Enter "c" to continue (this may cause an error), or <Enter> to quit.\n>>> ')

                    if keep_going == 'c':
                        continue
                    else:
                        sys.exit()

            self.connection.commit()

    def set_name(self, name):
        """Sets the Name attribute."""
        self.Name = ''.join(name)
        return

    def update_name(self, entry):
        """Inserts the Name attribute into the SQL table for the current working file."""
        query = f'UPDATE {self.working_file[:-4]} SET Name = ? WHERE entry = ?'
        self.cursor.execute(query, (self.Name, entry))
        return

    def set_description(self, description):
        """Sets the Description attribute."""
        self.Description = ''.join(description)
        return

    def update_description(self, entry):
        """Inserts the Description attribute into the SQL table for the current working file."""
        query = f'UPDATE {self.working_file[:-4]} SET Description = ? WHERE entry = ?'
        self.cursor.execute(query, (self.Description, entry))
        return

    def set_id(self, id_):
        """Sets the ID attribute."""
        if not id_:
            input(f'ID not found. Check ID for {self.Name} in {self.working_file}. Press <Enter> to continue.\n')
            return

        self.ID = int(id_[0])
        return

    def update_id(self, entry):
        """Inserts the ID attribute into the SQL table for the current working file."""
        try:
            query = f'UPDATE {self.working_file[:-4]} SET ID = ? WHERE entry = ?'
            self.cursor.execute(query, (self.ID, entry))
        except sqlite3.IntegrityError as error_message:
            default_color = helpers.DEFAULT_COLOR  # To avoid line character count PEP limit
            print(f'{helpers.YELLOW}Invalid ID for Job with ID {self.ID} in file {self.working_file}.{default_color}')
            print(f'Error from attempted SQL row insertion: {helpers.RED}{error_message}{helpers.DEFAULT_COLOR}')
            print(f'A negative integer will be inserted into the table in place of {self.ID}.')
            query = f'UPDATE {self.working_file[:-4]} SET ID = ? WHERE entry = ?'
            self.cursor.execute(query, (self.error_num, entry))
            self.error_num -= 1
            input("Press <Enter> to continue.\n")

        return

    def set_enabled(self, enabled):
        """Sets the Enabled attribute."""
        if not enabled:
            input(f'''Enabled status not found. Check ID for {self.Name} in {self.working_file}.
            Press <Enter> to continue.\n''')
            return

        self.Enabled = int(enabled[0])
        return

    def update_enabled(self, entry):
        """Inserts the Enabled attribute into the SQL table for the current working file."""
        query = f'UPDATE {self.working_file[:-4]} SET Enabled = ? WHERE entry = ?'
        self.cursor.execute(query, (self.Enabled, entry))
        return

    def set_command(self, command):
        """Sets the Command attribute."""
        self.Command = ''.join(command)
        return

    def update_command(self, entry):
        """Inserts the Command attribute into the SQL table for the current working file."""
        query = f'UPDATE {self.working_file[:-4]} SET Command = ? WHERE entry = ?'
        self.cursor.execute(query, (self.Command, entry))
        return

    def set_parentobject(self, parent_object):
        """Sets the ParentObject attribute."""
        if not parent_object:
            return

        self.ParentObject = int(parent_object[0])
        return

    def update_parentobject(self, entry):
        """Inserts the ParentObject attribute into the SQL table for the current working file."""
        query = f'UPDATE {self.working_file[:-4]} SET ParentObject = ? WHERE entry = ?'
        self.cursor.execute(query, (self.ParentObject, entry))
        return

    def set_triggerrules(self, trigger_rules):
        """Sets the TriggerRules attribute."""
        self.TriggerRules = ': '.join(trigger_rules)
        return

    def update_triggerrules(self, entry):
        """Inserts the TriggerRules attribute into the SQL table for the current working file."""
        query = f'UPDATE {self.working_file[:-4]} SET TriggerRules = ? WHERE entry = ?'
        self.cursor.execute(query, (self.TriggerRules, entry))
        return

    def set_triggers(self, triggers):
        """Sets the Triggers attribute."""
        self.Triggers = ''.join(triggers)  # Currently unused and will always populate NULL into table
        return

    def update_triggers(self, entry):
        """Inserts the Triggers attribute into the SQL table for the current working file."""
        query = f'UPDATE {self.working_file[:-4]} SET Triggers = ? WHERE entry = ?'
        self.cursor.execute(query, (self.Triggers, entry))
        return

    def set_dependencies(self, dependencies):
        """Sets the Dependencies attribute."""
        self.Dependencies = ', '.join(list(map(str, list(map(int, dependencies)))))
        return

    def update_dependencies(self, entry):
        """Inserts the Dependencies attribute into the SQL table for the current working file."""
        query = f'UPDATE {self.working_file[:-4]} SET Dependencies = ? WHERE entry = ?'
        self.cursor.execute(query, (self.Dependencies, entry))
        return

    def set_onerror(self, on_error):
        """Sets the OnError attribute."""
        self.OnError = ''.join(on_error)
        return

    def update_onerror(self, entry):
        """Inserts the Enabled attribute into the SQL table for the current working file."""
        if self.OnError:
            query = f'UPDATE {self.working_file[:-4]} SET OnError = ? WHERE entry = ?'
            self.cursor.execute(query, (self.OnError, entry))
        else:
            query = f'SELECT * FROM {self.working_file[:-4]} WHERE ID = {self.ParentObject}'
            self.cursor.execute(query)
            row = self.cursor.fetchall()
            OnError = row[0][11]
            update_query = f'UPDATE {self.working_file[:-4]} SET OnError = ? WHERE entry = ?'
            self.cursor.execute(update_query, (OnError, entry))

        return


my_parser = XMLParser()
my_parser.main()
