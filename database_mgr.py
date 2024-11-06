from operator import truediv
import sqlite3

conn = sqlite3.connect('subscriptions.db')
cur = conn.cursor()

#Artists Table
cur.execute('''
            CREATE TABLE IF NOT EXISTS artists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                uri TEXT NOT NULL
                )
            ''')

#SUBSCRIBER table
cur.execute('''
            CREATE TABLE IF NOT EXISTS subscriber_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                artist_id INTEGER NOT NULL,
                last_fetched TEXT NOT NULL,
                FOREIGN KEY (artist_id) REFERENCES artists (id)
            )
            ''')
#
conn.commit()
conn.close()

def add_artist(uri, artist_name):
    conn = sqlite3.connect('subscriptions.db')
    cur = conn.cursor()
    if does_exist(uri) is False:
        cur.execute('INSERT INTO artists (name, uri) VALUES (?, ?)', (artist_name, uri))
    conn.commit()
    conn.close()
    
def subscribe_artist(artist_name, uri, user_id):
    conn = sqlite3.connect('subscriptions.db')
    cur = conn.cursor()    
    
    cur.execute('PRAGMA foreign_keys = ON;')
    
    cur.execute('SELECT id FROM artists WHERE uri = ?', (uri,))
    artist = cur.fetchone()
    
    if artist:
        artist_id= artist[0]
    else:
        cur.execute('INSERT INTO artists (name, uri) VALUES (?, ?)', (artist_name, uri))
        conn.commit()
        
    cur.execute('SELECT id FROM artists WHERE uri = ?', (uri,))
    result = cur.fetchone()
    
    if result:
        artist_id = result[0]
    else:
        print("Error: Artist could not be found after insertion.")
        conn.close()
        return
    if not check_if_exists(user_id, artist_id):
        cur.execute('INSERT INTO subscriber_list (user_id, artist_id, last_fetched) VALUES (?, ?, ?)', (user_id, artist_id, 'temp'))
        conn.commit()
    else:
        print("Subscription already exists.")
    
    conn.close()
    
def add_last_fetched(user_id, artist_id, last_fetched):
    conn = sqlite3.connect('subscriptions.db')
    cur = conn.cursor()
    cur.execute('UPDATE subscriber_list SET last_fetched = ? WHERE artist_id = ? AND user_id = ?', (last_fetched, artist_id, user_id))    
    conn.commit()
    conn.close()
    
def does_exist(uri):
    conn = sqlite3.connect('subscriptions.db')
    cur = conn.cursor()
    cur.execute('SELECT id FROM artists WHERE uri = ?', (uri,))
    artist_uri = cur.fetchone()
    
    if artist_uri:
        conn.close()
        return True
    else: 
        conn.close()
        return False
    
def check_if_exists(user_id, artist_id):
    conn = sqlite3.connect('subscriptions.db')
    cur = conn.cursor()
    
    cur.execute('SELECT id FROM subscriber_list WHERE user_id = ? AND artist_id = ?', (user_id, artist_id))
    artist = cur.fetchone()
    
    if artist: 
        conn.close()
        return True
    else: 
        conn.close()
        return False

def uri_by_id(artist_id):
    conn = sqlite3.connect('subscriptions.db')
    cur = conn.cursor()
    cur.execute('SELECT uri FROM artists WHERE id = ?', (artist_id,))
    artist_uri = cur.fetchone()
    conn.close()
    return artist_uri

def get_subscriber_list(user_id):
    conn = sqlite3.connect('subscriptions.db')
    cur = conn.cursor()
    
    cur.execute('SELECT * FROM subscriber_list WHERE user_id = ?', (user_id,))
    sub_list = cur.fetchall()
    conn.close()
    return sub_list
    
    
