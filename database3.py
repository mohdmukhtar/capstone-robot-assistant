import sqlite3
import datetime

DATABASE_NAME = 'assistant_data.db'

def get_db_connection():
    """Establishes and returns a connection to the database."""
    conn = sqlite3.connect(DATABASE_NAME, timeout=5) 
    conn.row_factory = sqlite3.Row
    return conn

# --- USER FUNCTIONS ---
def get_user_id_by_name(name, conn=None):
    """Retrieves a user's ID by name. Accepts an optional connection."""
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
        
    user = conn.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchone()
    
    if close_conn:
        conn.close()
        
    return user['id'] if user else None

def get_user_name_by_id(user_id):
    """Retrieves a user's name by ID."""
    conn = get_db_connection()
    user = conn.execute("SELECT name FROM users WHERE id = ?",(user_id,)).fetchone()
    conn.close()
    return user['name'] if user else None

# --- HELPER FUNCTION FOR RELATIVE DATES ---
def convert_relative_date_to_string(date_phrase):
    """
    Converts common relative date phrases (today, tomorrow, next week) 
    into a sortable YYYY-MM-DD string.
    """
    if not date_phrase:
        return None
        
    phrase_lower = date_phrase.lower().strip()
    today = datetime.date.today()

    if phrase_lower in ('today', 'now'):
        return today.strftime('%Y-%m-%d')
    elif phrase_lower in ('tomorrow', 'tmr'):
        return (today + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    elif 'next week' in phrase_lower:
        return (today + datetime.timedelta(weeks=1)).strftime('%Y-%m-%d')
    
    # Return as is if it's a fixed date string or complex phrase
    return date_phrase

# --- REMINDER CRUD FUNCTIONS ---
def add_reminder(user_id, task, due_date=None):
    """Adds a new reminder with an optional due date."""
    due_date_str = convert_relative_date_to_string(due_date)
    
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO reminders (user_id, task, due_date) VALUES (?, ?, ?)",
            (user_id, task, due_date_str)
        )
        conn.commit()
        print(f"📝 Task created for User {user_id}: '{task}' (Due: {due_date_str})")
    except sqlite3.OperationalError as e:
        print(f"❌ DATABASE ERROR: {e}")
    finally:
        conn.close()


def update_reminder_due_date(reminder_id, new_date):
    """Updates the due date of an existing reminder."""
    new_date_str = convert_relative_date_to_string(new_date)
    
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE reminders SET due_date = ? WHERE id = ?",
            (new_date_str, reminder_id)
        )
        conn.commit()
    finally:
        conn.close()
        

def mark_reminder_completed(reminder_id):
    """Marks a reminder as completed."""
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE reminders SET completed = 1 WHERE id = ?",
            (reminder_id,)
        )
        conn.commit()
    finally:
        conn.close()


def get_user_reminders(user_id):
    """
    Retrieves all active reminders for a user, 
    sorted by soonest due date (NULL dates last).
    """
    conn = get_db_connection()
    reminders = conn.execute(
        """
        SELECT task, due_date, id FROM reminders 
        WHERE user_id = ? AND completed = 0 
        ORDER BY due_date IS NULL ASC, due_date ASC, id ASC
        """,
        (user_id,)
    ).fetchall()
    conn.close()
    return [(r['task'], r['due_date'], r['id']) for r in reminders]


def get_reminder_by_keywords(user_id, keywords):
    """Retrieves a single reminder based on robust keyword matching."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    SELECT task, due_date, id FROM reminders 
    WHERE user_id = ? AND LOWER(task) LIKE ? AND completed = 0
    LIMIT 1
    """
    cursor.execute(query, (user_id, keywords))
    result = cursor.fetchone()
    conn.close()
    return (result['task'], result['due_date'], result['id']) if result else None


# --- DATABASE SETUP AND SEEDING ---
def initialize_database():
    """Sets up the initial tables in the database."""
    conn = get_db_connection()
    c = conn.cursor()

    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
    """)
    
    # Reminders table
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            task TEXT NOT NULL,
            due_date TEXT NULL,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()


def seed_database(conn):
    """Seeds the database with test users and tasks."""
    c = conn.cursor()
    from utils3 import get_default_users # Import here to avoid circular dependency
    USERS = get_default_users() 
    
    # 1. Insert default users
    existing_users = [row[0] for row in c.execute("SELECT name FROM users").fetchall()]
    users_to_insert = [(user,) for user in USERS if user not in existing_users]
    if users_to_insert:
        c.executemany("INSERT INTO users (name) VALUES (?)", users_to_insert)
        conn.commit()

    # 2. Insert test tasks (simplified by replacing date constants with strings)
    
    # Check if tasks already exist to prevent duplicates
    if c.execute("SELECT COUNT(*) FROM reminders").fetchone()[0] > 0:
        return # Tasks already seeded

    # Get user IDs
    mohamed_id = get_user_id_by_name('Mohamed', conn)
    surya_id = get_user_id_by_name('Surya', conn)
    patrick_id = get_user_id_by_name('Patrick', conn)

    # Data for bulk insertion
    tasks_to_insert = []

    # 1. Mohamed's Tasks
    if mohamed_id:
        tasks_to_insert.append((mohamed_id, "Develop a Speech Generation code for Mico", '2025-11-01'))
        tasks_to_insert.append((mohamed_id, "Meet with group to review the capstone project winter semester plans", '2025-11-14'))
        tasks_to_insert.append((mohamed_id, "Order the standard parts for the robot assembly", '2025-12-02'))

    # 2. Surya's Tasks
    if surya_id:
        tasks_to_insert.append((surya_id, "Update the team on the status of the Machine Vision code", '2025-11-09'))
        tasks_to_insert.append((surya_id, "Meet with supervisor to discuss final mechanical robot design", '2025-11-11'))
        tasks_to_insert.append((surya_id, "Test the camera integration with the robot head", '2026-01-14'))

    # 3. Patrick's Tasks
    if patrick_id:
        tasks_to_insert.append((patrick_id, "Write about the SolidWorks assembly on the engineering term report", '2025-11-24'))
        tasks_to_insert.append((patrick_id, "Print the robot neck for prototype testing", '2026-01-13'))
        tasks_to_insert.append((patrick_id, "Order the servo motors for proper neck rotation", '2026-02-09'))

    # Perform bulk insertion
    c.executemany("INSERT INTO reminders (user_id, task, due_date) VALUES (?, ?, ?)", tasks_to_insert)
    conn.commit()
    print("Database seeded with test tasks.")


if __name__ == '__main__':
    initialize_database()
    conn = get_db_connection()
    seed_database(conn)
    conn.close()
    