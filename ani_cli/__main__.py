import re
import shlex
import sys
import subprocess
import requests
from InquirerPy import inquirer

base_url: str = 'https://www1.gogoanime.cm'
program: str = 'mpv'

header: dict = {
    'user-agent': 'Mozilla/5.0'
}

session: requests.Session = requests.session()

def search(name: str) -> list:
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
    d = {}
    for match in matches:
        d[match[1]] = match[0]
    return d

def get_episode_count(anime_id: str) -> int:
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
        return 'Not found'
    episode_count = int(episodes[-1][1])
    return episode_count

def get_embed_link(anime_id: str, episode: int) -> str:
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
    match = re.search(pattern, response.text)
    if match is None:
        return None
    embed_link = f'https:{match.group(1)}'
    return embed_link

def get_link(embedded_link: str) -> str:
    '''
    Scrape m3u8 video source link from gogoanime
    params:
        embedded_link (str): gogoanime embedded link
    return:
        link (str): m3u8 link
    '''
    response: requests.Response = session.get(embedded_link, headers=header)

    link: str = re.search(r"\s*sources.*", response.text).group()
    link: str = re.search(r"https:.*(m3u8)|(mp4)", link).group()
    return link

def play_episode(anime_id: str, episode: int):
    '''
    Play episode
    params:
        anime_id (str): anime id for gogoanime url
        episode (int): episode to watch
    return:
        subprocess.popen process
    '''
    embed_link: str = get_embed_link(anime_id, episode)
    if embed_link is None:
        return print('Error: embed link not found')

    link: str = get_link(embed_link)
    process = subprocess.Popen(
        shlex.split(f'mpv --http-header-fields="Referer: {embed_link}" {link}'),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT
    )
    return process

def get_anime(name=None) -> str:
    '''
    Get anime title from user
    '''
    if name is None:
        name: str  = inquirer.text(message='Input anime title:').execute()

    search_result: list = search(name)

    if not search_result:
        print('No result found')
        return None, None

    anime_title: str = inquirer.select(
        message='Select anime to watch',
        choices=search_result
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
    episode: int = int(inquirer.text(message=F'Select episode to watch [1 - {ep_end}]').execute())
    while not (episode >= 1 and episode <= ep_end):
        episode: int = int(inquirer.text(message='Invalid episode, try again').execute())
    return episode

def main():
    '''
    Main
    '''
    if len(sys.argv) > 1:
        anime_title, anime_id = get_anime(' '.join(sys.argv[1:]))
    else:
        anime_title, anime_id = get_anime()

    while anime_title is None:
        anime_title, anime_id = get_anime()

    episode_count = get_episode_count(anime_id)

    episode = get_episode(episode_count)

    play_episode(anime_id, episode)

    action = ''
    while action != 'Quit':
        action: str = inquirer.select(
            message=f'Played {anime_title}, episode {episode}',
            choices= [
                'Replay the episode again',
                'Select episode',
                'Play next episode',
                'Search other anime',
                'Quit'
            ]
        ).execute()

        if action == 'Replay the episode again':
            play_episode(anime_id, episode)
        elif action == 'Play next episode':
            if episode+1 <= episode_count:
                episode += 1
                play_episode(anime_id, episode)
            else:
                print('No more episode to watch')
        elif action == 'Search other anime':
            anime_title, anime_id = get_anime()
            episode_count = get_episode_count(anime_id)
            play_episode(anime_id, get_episode(episode_count))
        elif action == 'Quit':
            sys.exit()

if __name__ == '__main__':
    main()
