import json
import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import requests
import youtube_dl

from exceptions import ResponseException
from secrets import spotify_token, spotify_user_id


class CreatePlaylist:
    def __init__(self):
        self.youtube_client = self.get_youtube_client()
        self.all_song_info = {}

    def get_youtube_client(self):
        """ Log Into Youtube, Copied from Youtube Data API """
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret.json"

        # Get credentials and create an API client
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_console()

        # from the Youtube DATA API
        youtube_client = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials)

        return youtube_client

    def get_liked_videos(self):
        """Grab Our Liked Videos & Create A Dictionary Of Important Song Information"""
        request = self.youtube_client.playlists().list(
            part="snippet,contentDetails, id",
            mine="True"
        )
        response = request.execute()
        # collect each video and get important information
        for item_pl in response["items"]:
            request = self.youtube_client.playlistItems().list(
                part="snippet, contentDetails, id",
                playlistId=item_pl["id"]
            )
            
            response_vid = request.execute()

            print("vid items")

            for item in response_vid["items"]:                
                video_title = item["snippet"]["title"]
                print("-----------PLAYLIST ID: ", item_pl["id"])
                youtube_url = "https://www.youtube.com/watch?v={}".format(
                    item["snippet"]["resourceId"]["videoId"])
                print("ID IS: ", item["snippet"]["resourceId"]["videoId"])
                # use youtube_dl to collect the song name & artist name
                try:
                    video = youtube_dl.YoutubeDL({}).extract_info(
                        youtube_url, download=False)
                except:
                    ResponseException("YoutubeDL fuck u")
                    continue

                song_name = video["track"]
                artist = video["artist"]
                print("printing song name: ", song_name)
                if song_name is not None and artist is not None:
                    print("INSIDE LOOP!!!!")
                    print(song_name)
                    print(artist)
                    # save all important info and skip any missing song and artist
                    self.all_song_info[video_title] = {
                        "youtube_url": youtube_url,
                        "song_name": song_name,
                        "artist": artist,

                        # add the uri, easy to get song to put into playlist
                        "spotify_uri": self.get_spotify_uri(song_name, artist)

                }

    def create_playlist(self):
        """Create A New Playlist"""
        request_body = json.dumps({
            "name": "spotting",
            "description": "me doing things",
            "public": True
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format(
            spotify_user_id)
        response = requests.post(
            query,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        print("SPOTIFY RESPONSE")
        print(response_json)
        # playlist id
        return response_json["id"]

    def get_spotify_uri(self, song_name, artist):
        """Search For the Song"""
        print("Search for the song")
        print(song_name,"  ",artist)
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20".format(
            song_name,
            artist
        )
        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        print("SEARCH RESPONSE: ", response_json)
        songs = response_json["tracks"]["items"]

        # only use the first song
        uri = songs[0]["uri"]

        return uri

    def add_song_to_playlist(self):
        """Add all liked songs into a new Spotify playlist"""
        # populate dictionary with our liked songs
        self.get_liked_videos()

        # collect all of uri
        uris = [info["spotify_uri"]
                for song, info in self.all_song_info.items()]

        # create a new playlist
        playlist_id = self.create_playlist()

        # add all songs into new playlist
        request_data = json.dumps(uris)

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(
            playlist_id)

        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        print("add song response")
        print(response.json())
        # check for valid response status
        if response.status_code != 200:
            raise ResponseException(response.status_code)

        response_json = response.json()
        return response_json


if __name__ == '__main__':
    cp = CreatePlaylist()
    cp.add_song_to_playlist()