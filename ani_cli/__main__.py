import re
import shlex
import sys
import subprocess
import argparse
from typing import Union, Tuple
import requests
from InquirerPy import inquirer

base_url: str = 'https://www1.gogoanime.cm'
program: str = 'mpv'

header: dict = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
    'referer':'https://www.google.com/'
}

session: requests.Session = requests.session()

def search(name: str) -> dict:
    '''
    Scrape anime from gogoanime search page
    params:
        name (str): anime name
    return:
        d (dict): {anime_title: anime_id}'''
    response: requests.Response = session.get(
        f'{base_url}//search.html',
        params = {'keyword': name},
        headers=header
    )
    pattern: str = r'<div class="img">\s*<a href="/category/(.+)" title="(.+)">'
    matches: list = re.findall(pattern, response.text)
    d: dict = {}
    for match in matches:
        d[match[1]] = match[0]
    return d

def get_episode_count(anime_id: str) -> Union[int, None]:
    '''
    Scrape episode avaliable count
    params:
        anime_id (str): anime id for gogoanime url
    return:
        episode_count (int): total episode avaliable
    '''
    response: requests.Response = requests.get(f'{base_url}//category/{anime_id}', headers=header)
    pattern: str = r'''ep_start\s?=\s?['"]([0-9]+)['"]\sep_end\s?=\s?['"]([0-9]+)['"]>'''
    episodes: list = re.findall(pattern, response.text)
    if episodes == []:
        return None
    episode_count: int = int(episodes[-1][1])
    return episode_count

def get_embed_link(anime_id: str, episode: int) -> Union[str, None]:
    '''
    Scrape embed link from gogoanime
    params:
        anime_id (str): anime id for gogoanime url
        episode (int): episode to scrape
    return:
        embed_link (str): embed link of that episode
    '''
    response: requests.Response = session.get(
        f'{base_url}/{anime_id}-episode-{episode}',
        headers=header
    )
    pattern: str = r'''data-video="(.*?embedplus\?.*?)"\s?>'''
    match: re.Match = re.search(pattern, response.text)
    if match is None:
        return None
    return f'https:{match.group(1)}'

def get_link(episode_id: str) -> list:
    '''
    Scrape m3u8 video source link from gogoanime
    params:
        episode_id (str): gogoplay episode id
    return:
        link (str): m3u8 link
    '''
    response: requests.Response = session.get(f'https://gogoplay1.com/download?{episode_id}', headers=header)

    links: list = re.findall(r'href="(https?:\/\/.+?\.com\/.+?expiry=[0-9]+)"', response.text)

    return links

def play_episode(anime_id: str, episode: int, select_quality: bool):
    '''
    Play episode
    params:
        anime_id (str): anime id for gogoanime url
        episode (int): episode to watch
    return:
        subprocess.popen process
    '''

    embed_link = get_embed_link(anime_id, episode)
    if embed_link is None:
        print('Error: embed link not found')
        return None

    episode_id: re.Match = re.search(r'id=(.+?&)', embed_link)

    if episode_id is None:
        return None

    episode_id: str = episode_id.group(0)

    links: list = get_link(episode_id)
    if links == []:
        print('Cannot find video links')
        return None

    qualitys: dict = {}
    for link in links:
        qualitys[re.search(r'([0-9]+)p\.(?:mp4|m3u8)', link).group(1)] = link

    if select_quality:
        quality: str = inquirer.select(
            message='Select quality',
            choices=list(qualitys.keys())[::-1]
        ).execute()
        link: str = qualitys[quality]
    else:
        link: str = qualitys[list(qualitys.keys())[-1]]

    process = subprocess.Popen(
        shlex.split(f'mpv --http-header-fields="Referer: https://gogoplay1.com/download?{episode_id}" {link.replace("amp;", "")}'),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
    )
    return process

def get_anime(name=None) -> Union[Tuple[str, str], Tuple[None, None]]:
    '''
    Get anime title from user
    '''
    if name is None:
        name = inquirer.text(message='Input anime title:').execute()

    search_result: dict = search(name)

    if not search_result:
        print('No result found')
        return None, None

    anime_title: str = inquirer.select(
        message='Select anime to watch',
        choices=list(search_result.keys())
    ).execute()

    anime_id = search_result[anime_title]

    return anime_title, anime_id

def get_episode(ep_end: int) -> int:
    '''
    Asks user to select episode to watch
    params:
        ep_end (int): Last episode
    return:
        episode (int)
    '''
    while True:
        try:
            episode = int(inquirer.text(message=F'Select episode to watch [1 - {ep_end}]').execute())
        except ValueError:
            continue
        while not (episode >= 1 and episode <= ep_end):
            episode: int = int(inquirer.text(message='Invalid episode, try again').execute())
        break
    return episode

def main():
    '''
    Main
    '''

    try:
        parser = argparse.ArgumentParser(description='argparse')
        parser.add_argument('-q', '--quality', action='store_true', help='specify this if you want to select quality')
        parser.add_argument('rest', nargs=argparse.REMAINDER)

        args = parser.parse_args()

        if args.rest != []:
            anime_title, anime_id = get_anime(' '.join(args.rest))
        else:
            anime_title, anime_id = get_anime()

        while anime_title is None or anime_id is None:
            anime_title, anime_id = get_anime()

        episode_count = get_episode_count(anime_id)

        if episode_count is None:
            print('Error getting episode count')
            sys.exit()

        episode = get_episode(episode_count)

        play_episode(anime_id, episode, args.quality)

        action = ''
        while action != 'Quit':
            action: str = inquirer.select(
                message=f'Playing {anime_title}, episode {episode}',
                choices= [
                    'Replay the episode again',
                    'Select episode',
                    'Play next episode',
                    'Search other anime',
                    'Quit'
                ]
            ).execute()

            if action == 'Replay the episode again':
                play_episode(anime_id, episode, args.quality)
            elif action == 'Play next episode':
                if episode+1 <= episode_count:
                    episode += 1
                    play_episode(anime_id, episode, args.quality)
                else:
                    print('No more episode to watch')
            elif action == 'Search other anime':
                anime_title, anime_id = get_anime()
                episode_count = get_episode_count(anime_id)
                play_episode(anime_id, get_episode(episode_count), args.quality)
            elif action == 'Quit':
                sys.exit()
    except KeyboardInterrupt:
        print('Exiting...')
        sys.exit()

if __name__ == '__main__':
    main()
