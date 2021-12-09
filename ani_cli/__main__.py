import re
import requests
import sys
from InquirerPy import inquirer, utils
import os
import subprocess

base_url: str = 'https://www1.gogoanime.cm'
program: str = 'mpv'

header = {
    'user-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36',
}

session = requests.session()

def search(name: str) -> list:
    r: requests.Response = session.get(f'{base_url}//search.html', params = {'keyword': name}, headers=header)
    pattern: str = r'<div class="img">\s*<a href="/category/(.+)" title="(.+)">'
    matches: list = re.findall(pattern, r.text)
    d = {}
    for match in matches:
        d[match[1]] = match[0]
    return d

def get_episode_count(anime_id: str) -> int:
    r: requests.Response = requests.get(f'{base_url}//category/{anime_id}', headers=header)
    pattern = r'''ep_start\s?=\s?['"]([0-9]+)['"]\sep_end\s?=\s?['"]([0-9]+)['"]>'''
    episodes = re.search(pattern, r.text)
    if episodes == None:
        return 'Not found'
    return int(episodes.group(1)), int(episodes.group(2))

def get_embed_link(anime_id: str, episode: int) -> str:
    r: requests.Response = requests.get(f'{base_url}/{anime_id}-episode-{episode}', headers=header)
    pattern = r'''data-video="(.*?embedplus\?.*?)"\s?>'''
    match = re.search(pattern, r.text)
    if match == None:
        return None
    return f'https:{match.group(1)}'

def get_link(embedded_link: str) -> str:
    r = session.get(embedded_link, headers=header)

    link = re.search(r"\s*sources.*", r.text).group()
    link = re.search(r"https:.*(m3u8)|(mp4)", link).group()
    return link

def play_episode(anime_id: str, episode: int):
    embed_link: str = get_embed_link(anime_id, episode)
    if embed_link == None:
        return(print('Error: embed link not found'))

    link: str = get_link(embed_link)

    mpv = subprocess.Popen(f'mpv --http-header-fields="Referer: {embed_link}" {link}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    return mpv

def get_anime_id(name=None):
    if name == None:
        name: str  = inquirer.text(message='Input anime title:').execute()

    search_result: list = search(name)

    if search_result == {}:
        print('No result found')
        return

    anime_title: str = inquirer.select(
        message='Select anime to watch',
        choices=search_result
    ).execute()

    anime_id = search_result[anime_title]

    return anime_id

def get_episode(ep_end):
    episode: int = int(inquirer.text(message=F'Select episode to watch [1 - {ep_end}]').execute())
    while not (episode >= 1 and episode <= ep_end):
        episode: int = int(inquirer.text(message=F'Invalid episode, try again').execute())
    return episode

def main(name=None):
    if len(sys.argv) > 1:
        anime_id = get_anime_id(' '.join(sys.argv[1:]))
    else:
        anime_id = get_anime_id()

    ep_start, ep_end = get_episode_count(anime_id)

    episode = get_episode(ep_end)

    play_episode(anime_id, episode)
    
    action = ''
    while action != 'Quit':
        action: str = inquirer.select(
            message=f'Playing {anime_id}, episode {episode}',
            choices= [
                'Replay the episode again',
                'Select episode',
                'Play next episode',
                'Search other anime',
                'Quit'
            ]
        ).execute()

        if action == 'Replay the episode again':
            play_episode(episode)
        elif action == 'Play next episode':
            if episode+1 <= ep_end:
                episode += 1
                play_episode(episode)
            else:
                print('No more episode to watch')
        elif action == 'Search other anime':
            anime_id = get_anime_id()
            ep_end = get_episode_count(anime_id)
            play_episode(anime_id, get_episode(ep_end))
        elif action == 'Quit':
            exit()

if __name__ == '__main__': 
    main()