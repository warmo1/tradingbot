import sqlite3
import os
from typing import Iterable, Tuple, List, Optional

def db_path_from_url(url: str) -> str:
    if not url.startswith("sqlite:///"):
        raise ValueError("Only sqlite:/// URLs are supported in this starter.")
    return url.replace("sqlite:///", "", 1)

def get_conn(database_url: str) -> sqlite3.Connection:
    path = db_path_from_url(database_url)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        '''
        CREATE TABLE IF NOT EXISTS markets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exchange TEXT NOT NULL,
            symbol TEXT NOT NULL,
            base TEXT NOT NULL,
            quote TEXT NOT NULL,
            active INTEGER NOT NULL,
            listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(exchange, symbol)
        );
        CREATE TABLE IF NOT EXISTS candles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exchange TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            ts INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            UNIQUE(exchange, symbol, timeframe, ts)
        );
        CREATE INDEX IF NOT EXISTS idx_candles_symbol_time ON candles(symbol, timeframe, ts);
        CREATE TABLE IF NOT EXISTS paper_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            qty REAL NOT NULL,
            price REAL NOT NULL,
            fee REAL NOT NULL DEFAULT 0,
            note TEXT
        );
        -- Updated insights table for structured data
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            symbol TEXT NOT NULL UNIQUE, -- Store one insight per symbol
            signal TEXT NOT NULL, -- e.g., 'BUY', 'SELL', 'HOLD'
            justification TEXT NOT NULL
        );
        '''
    )
    conn.commit()

# --- New function to upsert insights ---
def upsert_insight(conn: sqlite3.Connection, symbol: str, signal: str, justification: str) -> None:
    ts = int(__import__("time").time() * 1000)
    conn.execute(
        """INSERT INTO insights (ts, symbol, signal, justification)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(symbol) DO UPDATE SET
             ts=excluded.ts, signal=excluded.signal, justification=excluded.justification
        """,
        (ts, symbol, signal, justification),
    )
    conn.commit()

# --- New function to get all insights ---
def get_all_insights(conn: sqlite3.Connection) -> List[dict]:
    cur = conn.execute("SELECT symbol, signal, justification FROM insights ORDER BY ts DESC")
    return [dict(row) for row in cur.fetchall()]

# (All other DB functions remain the same)
def upsert_market(conn: sqlite3.Connection, row: Tuple[str, str, str, str, int]) -> None:
    conn.execute(
        """INSERT INTO markets (exchange, symbol, base, quote, active)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(exchange, symbol) DO UPDATE SET
             base=excluded.base, quote=excluded.quote, active=excluded.active
        """,
        row,
    )
    conn.commit()

def bulk_insert_candles(conn: sqlite3.Connection, rows: Iterable[Tuple[str, str, str, int, float, float, float, float, float]]) -> None:
    conn.executemany(
        """INSERT OR IGNORE INTO candles (exchange, symbol, timeframe, ts, open, high, low, close, volume)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()

def get_symbols(conn: sqlite3.Connection, exchange: str, quote: Optional[str]=None) -> List[str]:
    if quote:
        cur = conn.execute("SELECT symbol FROM markets WHERE exchange=? AND quote=? AND active=1 ORDER BY symbol", (exchange, quote))
    else:
        cur = conn.execute("SELECT symbol FROM markets WHERE exchange=? AND active=1 ORDER BY symbol", (exchange,))
    return [r[0] for r in cur.fetchall()]

def get_latest_ts(conn: sqlite3.Connection, exchange: str, symbol: str, timeframe: str) -> Optional[int]:
    cur = conn.execute(
        "SELECT MAX(ts) FROM candles WHERE exchange=? AND symbol=? AND timeframe=?",
        (exchange, symbol, timeframe)
    )
    r = cur.fetchone()
    return int(r[0]) if r and r[0] is not None else None

def get_candles_df(conn: sqlite3.Connection, exchange: str, symbol: str, timeframe: str):
    import pandas as pd
    q = """        SELECT ts, open, high, low, close, volume
        FROM candles
        WHERE exchange=? AND symbol=? AND timeframe=?
        ORDER BY ts ASC
    """
    df = pd.read_sql_query(q, conn, params=(exchange, symbol, timeframe))
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        df = df.set_index("ts")
    return df

def paper_set(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO paper_state (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()

def paper_get(conn: sqlite3.Connection, key: str, default: Optional[str]=None) -> Optional[str]:
    cur = conn.execute("SELECT value FROM paper_state WHERE key=?", (key,))
    r = cur.fetchone()
    return r[0] if r else default

def paper_trade(conn: sqlite3.Connection, ts: int, symbol: str, side: str, qty: float, price: float, fee: float=0.0, note: str="") -> None:
    conn.execute(
        "INSERT INTO paper_trades (ts, symbol, side, qty, price, fee, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ts, symbol, side, qty, price, fee, note),
    )
    conn.commit()

def get_paper_trades_df(conn: sqlite3.Connection):
    import pandas as pd
    df = pd.read_sql_query("SELECT * FROM paper_trades ORDER BY ts ASC", conn)
    if not df.empty:
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df

def list_state_prefix(conn: sqlite3.Connection, prefix: str):
    cur = conn.execute("SELECT key, value FROM paper_state WHERE key LIKE ?", (prefix + "%",))
    return cur.fetchall()

def get_latest_close(conn: sqlite3.Connection, exchange: str, symbol: str):
    cur = conn.execute(
        "SELECT timeframe, MAX(ts) FROM candles WHERE exchange=? AND symbol=? GROUP BY timeframe ORDER BY MAX(ts) DESC LIMIT 1",
        (exchange, symbol),
    )
    row = cur.fetchone()
    if not row:
        return None
    timeframe = row[0]
    cur2 = conn.execute(
        "SELECT close FROM candles WHERE exchange=? AND symbol=? AND timeframe=? ORDER BY ts DESC LIMIT 1",
        (exchange, symbol, timeframe),
    )
    r2 = cur2.fetchone()
    return float(r2[0]) if r2 else None
