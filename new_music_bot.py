from os import name
from queue import Empty
from re import S
from tkinter import Y
import spotipy
import time
from datetime import date, datetime
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, url_for, session, redirect, g

import database_mgr

app = Flask(__name__)

app.config['SESSION_COOKIE_NAME']= 'Spotify Cookie'
app.secret_key = '**********'

TOKEN_INFO = 'token_info'

@app.route('/')
def login():
    auth_url = create_spotify_oauth().get_authorize_url()
    return redirect(auth_url)


@app.route('/redirect')
def spot_redirect():
    session.clear()
    code = request.args.get('code') #auth code in request parameters extracted and stored in code
    token_info = create_spotify_oauth().get_access_token(code) #exchanges auth code for access token which is stored as this var
    session[TOKEN_INFO] = token_info
    url_redirect = url_for('save_new_music', _external = True)
    return redirect(url_redirect)

def get_sp_client():
    if 'sp' not in g:
        try: 
            token_info = get_token()
            if token_info is None:
                print('User not logged in')
                return redirect("/")
        except:
            print('User not logged in')
            return redirect("/")
        
        g.sp = spotipy.Spotify(auth=token_info['access_token'])
        return g.sp
    else:
        return g.sp

@app.route('/saveNewMusic') # type: ignore
def save_new_music():
    try: 
        token_info = get_token()
        if token_info is None:
            print('User not logged in')
            return redirect("/")
    except:
        print('User not logged in')
        return redirect("/")
    
    try:
        sp = get_sp_client()
        
        user = sp.current_user()
        user_id = user['id']  # type: ignore
        follow_music_id = None
        
        user_playlists = sp.current_user_playlists()
        if user_playlists:
            current_playlists = user_playlists['items']
            
            for playlist in current_playlists:
                if (playlist['name'] == 'Weekly New Music'):
                    follow_music_id = playlist['id']
                    update_playlist(follow_music_id, user_id)

            if not follow_music_id:
                sp.user_playlist_create(user_id, "Weekly New Music", False, False, "This playlist is updated via a Python program created by Matt Evitts")
                update_playlist(follow_music_id, user_id)
                    
            if current_playlists:
                return current_playlists
            else:
                return "-1"
            
            
        
    except:
        print('Error Saving')
        return redirect("/")
                        


def update_artists():
    sp = get_sp_client()
    user = sp.current_user()
    user_id = user['id']  # type: ignore
    
    #cycle through adding new artists
    answer = input('Do you have more artists to add? y/n: ')
    while answer == 'y':
        artist_name = input('Add artist: ')
        uri = get_artist_uri(artist_name)
        database_mgr.add_artist(uri, artist_name)
        database_mgr.subscribe_artist(artist_name, uri, user_id) #add to database, 3rd is user id
        answer = input('Do you have more artists to add? y/n: ')
    return 

def get_artist_uri(artist_name):
    sp = get_sp_client()
    
    #check main db if already exists??
    results = sp.search(q=artist_name, limit=1, type='artist')
    items = results['artists']['items']
    if items:
        uri = items[0]['uri']
        return uri
    else:
        raise ValueError("Artist not found")
    
@app.route('/get-artist-uri', methods=['GET'])
def get_artist_uri_route():
    artist_name = request.args.get('artist_name')
    if not artist_name:
        return {"error": "Artist name is required"}, 400
    try:
        uri = get_artist_uri(artist_name)
        return {"error": uri}, 200
    except ValueError as e:
        return {"error": str(e)}, 404

def update_playlist(playlist_id, user_id):
    sp = get_sp_client()
    update_artists()
    subscribed_artists = database_mgr.get_subscriber_list(user_id)
    start_date = get_start_date()
    
    for artist in subscribed_artists:
        album, last_release_date = fetch_last_release(artist[2], start_date)
        
        if not album:
            print("Empty")
            continue
        else:
            database_mgr.add_last_fetched(user_id, artist[2], last_release_date)
            album_tracks = get_album_items(album)
            if album_tracks:
                sp.playlist_add_items(playlist_id, album_tracks)
                print("Added")
        
    return

def get_start_date():
    response = input("Do you want to 1.) Update starting today or 2.) A date from the past? 1/2: ")
    ask = True
    while (ask):
        if response == '1':
            start_date = datetime.today()
            ask = False
        elif response == '2':
            start_date = input('Input start date. Only year is required. (yyyy-mm-dd): ')
            ask = False
        else:
            print('invalid response. Please type 1 or 2.')
            response = input("Do you want to 1.) Update starting today or 2.) A date from the past? 1/2: ")
    return start_date


def get_album_items(album):
    track_uri = []
    tracks = album['tracks']['items']
    for track in tracks:
        track_uri.append(track['uri'])
    return track_uri

def parse_start_date(start_date):
    if len(start_date) == 4:
        return datetime.strptime(start_date, '%Y')
    elif len(start_date) == 7:
        return datetime.strptime(start_date, '%Y-%m')
    elif len(start_date) == 10:
        return datetime.strptime(start_date, '%Y-%m-%d')

    
def fetch_last_release(artist_id, start_date):
    sp = get_sp_client()
    release_dates = {}
    uri = database_mgr.uri_by_id(artist_id)
    
    new_date = parse_start_date(start_date)
    
    albums = sp.artist_albums(uri[0], include_groups='compilation,single,album', limit=40)
    if albums:
        items = albums['items']
        for item in items:
            release_date = parse_release_date(item['release_date'], item['release_date_precision'])
            if release_date >= new_date:
                release_dates[item['id']] = release_date
            else:
                continue
    else:
        print("no new content")
        return None, None
        
        #album_id is the var in lambda, iterates through release_dates, and is the key to compare
    last_album_id = max(release_dates, key=lambda album_id: release_dates[album_id]) #gets most recent release date and corresponding album id from dictionary
    last_release_date = release_dates[last_album_id]
    return sp.album(last_album_id), last_release_date
    

def get_token():
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        redirect(url_for('login', _external=False))
        
    now = int(time.time())
    
    if token_info is not None:
        #checks tokeninfo's knowledge of when it expires and compares it to now
        is_expired = token_info['expires_at'] - now < 60
        if(is_expired):
            spotify_oauth = create_spotify_oauth()
            token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])
        return token_info    

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id='6cc3f79938744cff9dde775de3794cdb',
        client_secret='a54b0ca05b3a42baacc14c9da2513b20',
        redirect_uri=url_for('spot_redirect', _external=True),
        scope='user-library-read playlist-modify-public playlist-modify-private playlist-read-private'
        )
    
def parse_release_date(release_date, precision):
    if precision == 'year':
        return datetime.strptime(release_date, '%Y')
    elif precision == 'month':
        return datetime.strptime(release_date, '%Y-%m')
    elif precision == 'day':
        return datetime.strptime(release_date, '%Y-%m-%d')
    else:
        raise ValueError(f"Unsuppoertd precision: {precision}")
    
    
#app.run(debug=True)
