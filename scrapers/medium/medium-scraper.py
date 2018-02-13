from urllib.error import HTTPError
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import json


def open_url(url):
    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
    req = Request(url, None, hdr)
    rsp = urlopen(req)
    return BeautifulSoup(rsp, 'html.parser')

main_page = open_url('http://medium.com')

main_links = [e.a['href'] for e in main_page.find_all('span', class_='ds-nav-text')]


post_links = []

for ml in main_links:
    sub_page = open_url(ml)
    post_links += [e['href'] for e in sub_page.find_all('a') if 'data-post-id' in e.attrs]

post_links = list(set(post_links))


data = {'posts' : []}

for pl in post_links:
    post_data = {}
    post_data['url'] = pl
    try:
        post_page = open_url(pl)
    except HTTPError:
        print('HTTPError occured, skipping URL: {}'.format(pl))
        continue
    # Title
    try:
        content = post_page.find_all('h1', class_='graf--title')
        post_data['title'] = content[0].text
    except IndexError:
        post_data['title'] = None
    # Text
    try:
        pars = post_page.find_all('p')
        text = [p.text for p in pars]
        post_data['text'] = ' '.join(text)
    except AttributeError:
        post_data['text'] = None
    # Date & Time
    try:
        time = post_page.find('time')
        post_data['datetime'] = time['datetime']
    except AttributeError:
        post_data['datetime'] = None
    # Author
    try:
        author = post_page.find_all('a', {'data-action':'show-user-card'}, class_='ds-link')
        post_data['author'] = author[0].text
    except IndexError:
        post_data['author'] = None
    # Claps
    try:
        claps = post_page.find('button', {'data-action':'show-recommends'})
        if claps.text[-1:] == 'K':
            post_data['claps'] = int(float(claps.text[:-1]) * 1000)
        else:
            post_data['claps'] = claps.text
    except AttributeError:
        post_data['claps'] = None
    data['posts'].append(post_data)

print('Scraped {} posts from medium.com'.format(len(data['posts'])))

with open('medium-sample.json', 'w') as file:
    json.dump(data, file)

