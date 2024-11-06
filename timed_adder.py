from new_music_bot import app, get_sp_client, update_playlist, spotipy

with app.app_context():
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
                break

        if not follow_music_id:
            new_playlist = sp.user_playlist_create(user_id, "Weekly New Music", False, False, "This playlist is updated via a Python program created by Matt Evitts")
            follow_music_id = new_playlist['id']
                    
    if follow_music_id:
        update_playlist(follow_music_id, user_id)
    else:
        print("couldn't find")
