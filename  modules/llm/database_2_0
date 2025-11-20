import sqlite3
import datetime

# --- DATABASE CONFIGURATION ---
DB_NAME = 'assistant_data.db'

def init_db():
    """Initializes the database and creates the necessary tables."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. User Table: Stores user ID and Name
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        )
    """)

    # 2. Reminders/Tasks Table: Stores the actual data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            due_date TEXT,
            is_completed INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()

# --- USER MANAGEMENT ---
def add_user(user_id: int, name: str):
    """Adds or updates a user in the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        # Use INSERT OR IGNORE to only add if the ID doesn't exist
        cursor.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (user_id, name))
        conn.commit()
        print(f"✅ User ID {user_id} ({name}) added/checked.")
    except Exception as e:
        print(f"❌ Error adding user: {e}")
    finally:
        conn.close()

def get_user_id_by_name(name: str):
    """Retrieves the user ID based on a provided name (case-insensitive)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Use LIKE for case-insensitive search
    cursor.execute("SELECT id FROM users WHERE name LIKE ?", (name.strip(),))
    user_id = cursor.fetchone()
    conn.close()
    return user_id[0] if user_id else None

def get_user_name_by_id(user_id: int):
    """Retrieves the user name based on a provided ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
    user_name = cursor.fetchone()
    conn.close()
    return user_name[0] if user_name else "Unknown User"


# --- REMINDER MANAGEMENT ---
def add_reminder(user_id: int, description: str, due_date: str = None):
    """Adds a new reminder for a specific user."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reminders (user_id, description, due_date) VALUES (?, ?, ?)",
        (user_id, description, due_date)
    )
    conn.commit()
    conn.close()
    return cursor.lastrowid

def get_user_reminders(user_id: int, is_completed: int = 0):
    """Retrieves all non-completed reminders for a specific user."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT description, due_date, reminder_id FROM reminders 
        WHERE user_id = ? AND is_completed = ? 
        ORDER BY due_date ASC
    """, (user_id, is_completed))
    reminders = cursor.fetchall()
    conn.close()
    return reminders

def mark_reminder_completed(reminder_id: int):
    """Marks a reminder as completed."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET is_completed = 1 WHERE reminder_id = ?", (reminder_id,))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # Initialize and populate the database when this script is run directly
    print("--- Initializing User Database ---")
    init_db()
    
    # --- SETUP EXAMPLE USERS (Matching your AI Machine Vision names) ---
    print("\nSetting up example users (IDs 1, 2, 3):")
    add_user(1, 'Surya')
    add_user(2, 'Patrick')
    add_user(3, 'Alex') # Adding "Alex" for testing the database functionality
    
    # --- ADD EXAMPLE REMINDERS ---
    print("\nAdding Example Reminders...")
    add_reminder(user_id=1, description="Call the capstone professor", due_date="2025-11-21")
    add_reminder(user_id=2, description="Check the ESP32 communication protocol")
    add_reminder(user_id=3, description="Buy new batteries for the servo motors")
    
    print("\n--- Current Reminders for User 1 (Surya) ---")
    reminders = get_user_reminders(user_id=1)
    for desc, due, r_id in reminders:
        print(f"ID {r_id}: {desc} (Due: {due if due else 'N/A'})")
        
    print("\nInitialization Complete. Run 'python modules/llm/database_2.0.py' once to setup test data.")
    