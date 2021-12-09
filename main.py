import re
import requests
import sys
from InquirerPy import inquirer
import os

base_url: str = 'https://www1.gogoanime.cm'

header = {
    'user-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.101 Safari/537.36',
}

session = requests.session()

def search(name: str) -> list:
    r: requests.Response = session.get(f'{base_url}//search.html', params = {'keyword': name}, headers=header)
    # pattern = r'<a href="(/category/.+)" title="(.+)">.*<p class="name"'
    pattern: str = r'<div class="img">\s*<a href="/category/(.+)" title="(.+)">'
    matches: list = re.findall(pattern, r.text)
    d = {}
    for match in matches:
        d[match[1]] = match[0]
    return d

def search_episode(anime_id: str) -> int:
    r: requests.Response = requests.get(f'{base_url}//category/{anime_id}', headers=header)
    pattern = r'''ep_start\s?=\s?['"]([0-9]+)['"]\sep_end\s?=\s?['"]([0-9]+)['"]>'''
    episodes = re.search(pattern, r.text)
    if episodes == None:
        return 'Not found'
    return int(episodes.group(1)), int(episodes.group(2))

def get_embed_link(anime_id: str, episode: int) -> str:
    r: requests.Response = requests.get(f'{base_url}/{anime_id}-episode-{episode}', headers=header)
    # print(r.text)
    pattern = r'''rel="100" data-video="(.*?)"\s?>'''
    match = re.search(pattern, r.text)
    if match == None:
        return None
    return f'https:{match.group(1)}'

def get_link(embedded_link: str) -> str:
    r = session.get(embedded_link, headers=header)

    link = re.search(r"\s*sources.*", r.text).group()
    link = re.search(r"https:.*(m3u8)|(mp4)", link).group()
    return link

def main():
    if len(sys.argv) > 1:
        name: str = ' '.join(sys.argv[1:])
    else:
        name: str  = inquirer.text(message='Input anime title:').execute()

    search_result: list = search(name)

    if search_result == {}:
        print('No result found')
        return

    anime_title: str = inquirer.select(
        message='Select anime to watch',
        choices=search_result
    ).execute()

    ep_start, ep_end = search_episode(search_result[anime_title])

    episode: int = int(inquirer.text(message=F'Select episode to watch [1, {ep_end}]').execute())
    
    while not (episode >= ep_start and episode <= ep_end):
        episode: int = int(inquirer.text(message=F'Invalid episode, try again').execute())
    
    embed_link: str = get_embed_link(search_result[anime_title], episode)
    if embed_link == None:
        return(print('Error: embed link not found'))

    link: str = get_link(embed_link)
    print(link)
    os.system(f'mpv --http-header-fields="Referer: {embed_link}" {link}')

if __name__ == '__main__': 
    exit(main())