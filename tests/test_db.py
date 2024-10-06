import sqlite3

def get_test_db_engine(db_name=":memory:"):
    """
    Returns a SQLite engine for a test database.
    
    Parameters:
    db_name (str): The name of the database. Defaults to in-memory database.
    
    Returns:
    sqlite3.Connection: SQLite connection object.
    """
    return sqlite3.connect(db_name)