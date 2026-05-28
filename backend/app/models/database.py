import sqlite3
from contextlib import contextmanager

class Database:

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None

    # ======================
    # CONNECT
    # ======================
    def connect(self):
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row

    # ======================
    # CLOSE
    # ======================
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    # ======================
    # EXECUTE (WRITE)
    # ======================
    def execute(self, query, params=None):
        self.connect()
        
        if self.conn is None:
            raise RuntimeError("Database connection failed")
        
        cursor = self.conn.cursor()
        cursor.execute(query, params or ())
        return cursor

    # ======================
    # EXECUTE MANY (BULK)
    # ======================
    def execute_many(self, query, params_list):
        self.connect()
        
        if self.conn is None:
            raise RuntimeError("Database connection failed")
        
        cursor = self.conn.cursor()
        cursor.executemany(query, params_list)
        return cursor

    # ======================
    # FETCH ONE
    # ======================
    def fetch_one(self, query, params=None):
        cursor = self.execute(query, params)
        return cursor.fetchone()

    # ======================
    # FETCH ALL
    # ======================
    def fetch_all(self, query, params=None):
        cursor = self.execute(query, params)
        return cursor.fetchall()

    # ======================
    # TRANSACTION CONTROL
    # ======================
    def begin(self):
        self.connect()
        
        if self.conn is None:
            raise RuntimeError("Database connection failed")
        
        self.conn.execute("BEGIN")

    def commit(self):
        if self.conn:
            self.conn.commit()

    def rollback(self):
        if self.conn:
            self.conn.rollback()

    # ======================
    # CONTEXT MANAGER
    # ======================
    @contextmanager
    def transaction(self):
        try:
            self.begin()
            yield
            self.commit()
        except Exception:
            self.rollback()
            raise