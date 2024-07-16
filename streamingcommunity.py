from tmdbv3api import TMDb, Movie, TV
import requests
import logging 
from bs4 import BeautifulSoup,SoupStrainer
from datetime import datetime
import dateparser
from convert import get_TMDb_id_from_IMDb_id
from info import get_info_tmdb, is_movie, get_info_imdb
import config
import json
import re
#Get domain
SC_DOMAIN= config.SC_DOMAIN
SC_FAST_SEARCH = config.SC_FAST_SEARCH

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.10; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Accept-Language': 'en-US,en;q=0.5'
}

#GET VERSION OF STREAMING COMMUNITY:
def get_version():
    #Extract the version from the main page of the site


    try:
        base_url = f'https://streamingcommunity.{SC_DOMAIN}/richiedi-un-titolo'
        response = requests.get(base_url, headers=headers)
        #Soup the response
        soup = BeautifulSoup(response.text, "lxml")

        # Extract version
        version = json.loads(soup.find("div", {"id": "app"}).get("data-page"))['version']
        return version
    except:
        print("Couldn't find the version")
        version = "65e52dcf34d64173542cd2dc6b8bb75b"
        return version

def search(query,date,ismovie):
    #Do a request to get the ID of serie/move and it's slug in the URL
    response = requests.get(query).json()
    for item in response['data']:
        tid = item['id']
        slug = item['slug']
        type = item['type']
        if type == "tv":
            type = 0
        elif type == "movie":
            type = 1
        if type == ismovie: 
            #Added a Check to see if the result is what it is supposed to be
            if SC_FAST_SEARCH == "0":
                if ismovie == 0:
                    seasons_count = item['seasons_count']
                    #Do not ask me why but somewhy streaming community call the first air date the last air date
                    first_air_date = item['last_air_date']
                    if first_air_date:
                        first_air_year = first_air_date.split("-")[0]
                        if first_air_year == date:
                            return tid,slug
                    else:
                        response = requests.get ( f'https://streamingcommunity.boston/titles/{tid}-{slug}')
                        pattern = r'<div[^>]*class="features"[^>]*>.*?<span[^>]*>(.*?)<\/span>'
                        match = re.search(pattern, response.text)
                        print(match.group(1).split("-")[0])
                        first_air_year = match.group(1).split("-")[0]
                        date = int(date)
                        first_air_year = int(first_air_year)
                        if first_air_year == date:
                            return tid,slug
                elif ismovie == 1:
                    return tid,slug
            elif SC_FAST_SEARCH == "1":
                return tid,slug
        else:
            print("Couldn't find anything")

        
def get_film(tid):
    #Access the iframe
    url = f'https://streamingcommunity.{SC_DOMAIN}/iframe/{tid}'
    response = requests.get(url, headers=headers)
    iframe = BeautifulSoup(response.text, 'lxml')
    #Get the link of iframe
    iframe = iframe.find('iframe').get("src")
    #Get the ID containted in the src of iframe
    vixid = iframe.split("/embed/")[1].split("?")[0]
    #Build the url with 1080p, to get the highest resolution
    url = f'https://vixcloud.co/playlist/{vixid}'
    return url

def get_season_episode_id(tid,slug,season,episode,version):
    #Set some basic headers for the request
    headers = {
            'user-agent': "Mozilla/5.0 (Windows NT 10.10; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            'x-inertia': 'true', 
            #Version of streaming community
            'x-inertia-version': version
        }   
      #Get episode ID 
    response = requests.get(f'https://streamingcommunity.{SC_DOMAIN}/titles/{tid}-{slug}/stagione-{season}', headers=headers)
    # Print the json got
    json_response = response.json().get('props', {}).get('loadedSeason', {}).get('episodes', [])
    for dict_episode in json_response:
        if dict_episode['number'] == episode:
            return dict_episode['id']

def get_episode_link(episode_id,tid):
    #The parameters for the request
    params = {
                'episode_id': episode_id, 
                'next_episode': '1'
            }
    #Let's try to get the link from iframe source
        # Make a request to get iframe source
    response = requests.get(f"https://streamingcommunity.{SC_DOMAIN}/iframe/{tid}", params=params)

    # Parse response with BeautifulSoup to get iframe source
    soup = BeautifulSoup(response.text, "lxml")
    iframe = soup.find("iframe").get("src")
    vixid = iframe.split("/embed/")[1].split("?")[0]
    url = f"https://vixcloud.co/playlist/{vixid}"
    return url


def streaming_community(imdb):
    try:
        general = is_movie(imdb)
        ismovie = general[0]
        imdb_id = general[1]
        type = "StreamingCommunity"
        if ismovie == 0 : 
            season = int(general[2])
            episode = int(general[3])
            #Check if fast search is enabled or disabled
            if SC_FAST_SEARCH == "1":
                if "tt" in imdb:
                #Get showname
                    showname = get_info_imdb(imdb_id,ismovie,type)
                    date = None
                else:
                    #I just set n season to None to avoid bugs, but it is not needed if Fast search is enabled
                    date = None
                    #else just equals them
                    tmdba = imdb_id.replace("tmdb:","")
                    showname = get_info_tmdb(tmdba,ismovie,type)
            elif SC_FAST_SEARCH == "0":
                tmdba = get_TMDb_id_from_IMDb_id(imdb_id)
                showname,date = get_info_tmdb(tmdba,ismovie,type)  
        #HERE THE CASE IF IT IS A MOVIE
        else:
            if "tt" in imdb:
                #Get showname
                date = None
                showname = get_info_imdb(imdb_id,ismovie,type)
            else:
                    #I just set n season to None to avoid bugs, but it is not needed if Fast search is enabled
                    #else just equals them
                    date = None
                    tmdba = imdb_id.replace("tmdb:","")
                    showname = get_info_tmdb(tmdba,ismovie,type) 

        showname = showname.replace(" ", "+").replace("–", "+").replace("—","+")
        query = f'https://streamingcommunity.{SC_DOMAIN}/api/search?q={showname}'
        tid,slug = search(query,date,ismovie)
        if ismovie == 1:
            #TID means temporaly ID
            url = get_film(tid)
            print(url)
            return url
        if ismovie == 0:
            #Uid = URL ID
            version = get_version()
            episode_id = get_season_episode_id(tid,slug,season,episode,version)
            url = get_episode_link(episode_id,tid)
            print(url)
            return url
    except Exception as e:
        print("Nope It failed")