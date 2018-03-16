# TODO: Filter – Grab only pages with specific keywords
# TODO: Filter – Grab posts written only after a specific date

from urllib.error import HTTPError
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
from pymongo import MongoClient
import datetime


def open_url(url):
    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
    req = Request(url, None, hdr)
    rsp = urlopen(req)
    return BeautifulSoup(rsp, 'html.parser')


def extract_main_links(main_url, html_el, css_class):
    """
    :param main_url: Main URL
    :param html_el: HTML element containing links to sub-pages
    :param css_class: Specific CSS class for said HTML element
    :return: List of URLs to sub-pages
    """
    main_page = open_url(main_url)
    try:
        main_links = [e.a['href'] for e in main_page.find_all(html_el, class_=css_class)]
        return main_links
    except AttributeError:
        print("Attribute error occurred while extracting links.")
        return None


def extract_post_links(main_url, html_el, css_class_nav, css_class_link):
    """
    :param main_url: Main URL
    :param html_el: HTML elements containing links to pages with posts/articles
    :param css_class_nav: Specific CSS class for said HTML element
    :param css_class_link: Specific CSS class for <a> elements in said HTML element
    :return: List of URLs to pages containing posts/articles
    """
    links = []
    for ml in extract_main_links(main_url, html_el, css_class_nav):
        sub_page = open_url(ml)
        links += [e['href'] for e in sub_page.find_all('a') if css_class_link in e.attrs]

    return list(set(links))


def extract_title(bs_obj, html_el, css_class):
    """
    :param bs_obj: Beautiful Soup Object
    :param html_el: HTML element containing title
    :param css_class: Specific CSS class for said HTML element
    :return: Content of element if found, else None
    """
    try:
        title_elem = bs_obj.find_all(html_el, class_=css_class)
        return title_elem[0].text
    except IndexError:
        return


def extract_text(bs_obj):
    """
    :param bs_obj: Beautiful Soup Object
    :return: Content of all <p> elements as one concatenated string
    """
    try:
        pars = bs_obj.find_all('p')
        text = [p.text for p in pars]
        return ' '.join(text)
    except AttributeError:
        return


def extract_datetime(bs_obj):
    """
    :param bs_obj: Beautiful Soup Object
    :return: Datetime attribute value of time element if found, else None
    """
    try:
        time = bs_obj.find('time')
        return time['datetime']
    except AttributeError:
        return


def extract_author(bs_obj, html_el, css_class, css_pairs):
    """
    :param bs_obj: Beautiful Soup Object
    :param html_el: HTML element containing author name
    :param css_class: Specific CSS class for said HTML element
    :param css_pairs: Specific pairs of CSS attributes and values for said HTML element
    :return: Content of element if found, else None
    """
    try:
        author = bs_obj.find_all(html_el, css_pairs, class_=css_class)
        return author[0].text
    except IndexError:
        return


def extract_likes(bs_obj, html_el, css_pairs):
    """
    :param bs_obj: Beautiful Soup Object
    :param html_el: HTML Element where likes are found
    :type html_el: str
    :param css_pairs: Specific pairs of CSS attributes and values for said HTML element
    :type css_pairs: dict
    :return: Content of element if found, else None
    """
    try:
        claps = bs_obj.find(html_el, css_pairs)
        if claps.text[-1:] == 'K':
            # Return full number if thousands abbreviated by 'K'
            return int(float(claps.text[:-1]) * 1000)
        else:
            return claps.text
    except AttributeError:
        return


post_links = extract_post_links('http://medium.com/', 'span', 'ds-nav-text', 'data-post-id')

data = {'posts': []}

for pl in post_links:
    post_data = dict()
    post_data['url'] = pl

    try:
        post_page = open_url(pl)
    except HTTPError:
        print("HTTPError occurred, skipping URL: {}".format(pl))
        continue

    post_data['title'] = extract_title(post_page, 'h1', 'graf--title')
    post_data['text'] = extract_text(post_page)
    post_data['datetime'] = extract_datetime(post_page)
    post_data['author'] = extract_author(post_page, 'a', 'ds-link', {'data-action': 'show-user-card'})
    post_data['claps'] = extract_likes(post_page, 'button', {'data-action': 'show-recommends'})

    data['posts'].append(post_data)


# Add metadata about the scraping process
data['scraper_metadata'] = {
    'scraper': 'medium-scraper',
    'time': datetime.datetime.now().isoformat()
}


# Add scraped posts to database
client = MongoClient('mongodb://localhost:27017')
db = client.hyptodata
posts = db.posts
posts.insert_one(data)
