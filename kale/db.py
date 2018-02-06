#stdlib
import sqlite3
import datetime
import getpass
import os.path


# Connect
def connect(db_path='~/.kale_status.db'):
    abs_path = os.path.expanduser(db_path)
    conn = sqlite3.connect(abs_path)
    return conn.cursor()

# Create tables

def create_wf_table(c):
    c.execute("""CREATE TABLE IF NOT EXISTS workflows(
    wf_id integer PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    wf_executor TEXT,
    owner TEXT,
    submitted DATE,
    status TEXT,
    modified DATE
    );""")

def create_task_table(c):
    c.execute("""CREATE TABLE IF NOT EXISTS tasks(
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    task_type TEXT,
    owner TEXT,
    submitted DATE,
    status TEXT,
    modified DATE
    );""")

def create_tag_table(c):
    c.execute("""CREATE TABLE IF NOT EXISTS tags(
    tag TEXT PRIMARY KEY
    );""")

# Create junction tables

def create_task_tag_junction_table(c):
    c.execute("""CREATE TABLE IF NOT EXISTS task_tag(
    junction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag TEXT,
    task_id INTEGER
    )""")

def create_wf_task_junction_table(c):
    """junction_id: SQL id of workflow/task relationship
    wf_id: SQL id of workflow
    task_id: SQL id of task
    task_index: kale index of task in workflow
    """
    c.execute("""CREATE TABLE IF NOT EXISTS wf_tasks(
    junction_id integer PRIMARY KEY AUTOINCREMENT,
    wf_id INTEGER,
    task_id INTEGER
    task_index INTEGER
    );""")

# Add items

def add_wf(c, wf_dict):
    """Store WF information in database.

    Parameters
    ----------
    wf_dict : dict      dill.loads(wf_bytes)

    Returns
    -------
    wf_id : int
    """
    c.execute(
        """INSERT INTO workflows
        (name, wf_executor, owner, submitted)
        VALUES (?, ?, ?, ?)""",
        [
            wf_dict['name'],
            wf_dict['wf_executor'],
            getpass.getuser(),
            datetime.datetime.now().timestamp()
        ]
    )
    wf_id = c.lastrowid

    for task_index, task_dict in wf_dict['index_dict_sanitized']:
        add_task(c, task_dict, wf_id, task_index)

    return wf_id

def add_task(c, task_dict, wf_id, task_index):
    """Call after workflow is created."""
    c.execute(
        """INSERT INTO tasks
        (task_name, task_type, owner, submitted)
        VALUES (?, ?, ?, ?, ?)""",
        [
            wf_dict['task_name'],
            wf_dict['task_type'],
            getpass.getuser(),
            datetime.datetime.now().timestamp()
        ]
    )

    task_id = c.lastrowid
    # Link to workflow
    link_task_to_wf(c, task_id, wf_id, task_index)

    # Link to tags
    if 'tags' in wf_dict:
        for tag in wf_dict['tags']:
            if not tag_exists(c, tag):
                add_tag(tag)
            link_tag_to_task(c, tag, task_id)

    return task_id

def add_tag(c, tag):
    c.execute(
        """INSERT INTO tags
        VALUES (?)""",
        [tag]
    )

# Link

def link_task_to_wf(c, task_id, wf_id, task_index):
    """junction_id: SQL id of workflow/task relationship
    wf_id: SQL id of workflow
    task_id: SQL id of task
    task_index: kale index of task in workflow
    """
    c.execute("""INSERT INTO wf_tasks
        (wf_id, task_id, task_index)
        VALUES (?, ?, ?);""",
        [task_id, wf_id, task_index]
    )
    junction_id = c.lastrowid
    return junction_id

def link_tag_to_task(c, tag, task_id):
    """junction_id: SQL id of task/tag relationship
    task_id: SQL id of task
    tag: name of tag
    """
    c.execute("""INSERT INTO task_tags
        (task_id, tag)
        VALUES (?, ?);""",
        [task_id, tag]
    )

    junction_id = c.lastrowid
    return junction_id

# Update

def update_wf_status(c, wf_id, status):
    c.execute(
        """UPDATE workflows
        SET status=?, modified=?
        WHERE wf_id = ?
        """,
        [
            status,
            datetime.datetime.now().timestamp(),
            wf_id
        ]
    )

def update_task_status(c, task_id, status):
    c.execute(
        """UPDATE tasks
        SET status=?, modified=?
        WHERE task_id = ?
        """,
        [
            status,
            datetime.datetime.now().timestamp(),
            task_id
        ]
    )

# Query status

def get_wf_status(c, wf_id):
    c.execute(
        """SELECT status FROM workflows
        WHERE wf_id = ?;
        """,
        [wf_id]
    )
    return c.fetchone()

def get_task_status(c, task_id):
    c.execute(
        """SELECT status FROM tasks
        WHERE task_id = ?;
        """,
        [task_id]
    )
    return c.fetchone()

# Query entry

def get_wf(c, wf_id):
    c.execute(
        """SELECT * FROM workflows
        WHERE wf_id = ?;
        """,
        [wf_id]
    )
    return c.fetchone()

def get_task(c, task_id):
    c.execute(
        """SELECT * FROM tasks
        WHERE task_id = ?;
        """,
        [task_id]
    )
    return c.fetchone()


# Query all entries

def get_all_wfs(c):
    c.execute("""SELECT * FROM workflows""")
    return c.fetchall()

def get_all_tasks(c):
    c.execute("""SELECT * FROM tasks""")
    return c.fetchall()


# Boolean queries

def tag_exists(c, tag):
    """Whether tag is stored in DB already"""

    c.execute("""SELECT * FROM tags
        WHERE tag = ?
        """,
        tag
    )

    # If the query returned results, the tag exists.
    if c.fetchone():
        return True
    else:
        return False

# Initialize

def init(c):
    """Initialize"""
    # Connect
    c = connect()

    # Create tables
    create_wf_table(c)
    create_task_table(c)
    create_tag_table(c)

    # Create junction tables
    create_task_tag_junction_table(c)
    create_wf_task_junction_table(c)

# Main

def main():
    c = connect()
    init(c)

if __name__ == '__main__':
    main()
