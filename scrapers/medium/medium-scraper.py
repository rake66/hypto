# TODO: Filter – Grab only pages with specific keywords

from urllib.error import HTTPError
from urllib.request import urlopen, Request
import urllib.parse
import unicodedata
from bs4 import BeautifulSoup
from pymongo import MongoClient
import datetime


def open_url_html(url):
    # Set header
    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}

    # Handle IRIs
    url = urllib.parse.urlsplit(url)
    url = list(url)
    url[2] = urllib.parse.quote(url[2])
    url = urllib.parse.urlunsplit(url)

    # Open URL and return BS object
    req = Request(url, None, hdr)
    rsp = urlopen(req)
    return BeautifulSoup(rsp, 'html.parser')


def open_url_xml(url):
    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'}
    req = Request(url, None, hdr)
    rsp = urlopen(req)
    return BeautifulSoup(rsp, 'lxml')


def extract_post_links(date_from):
    """
    :param date_from: Starting date for posts to be scraped, ISO format (YYYY-MM-DD)
    :return: list of URLs
    """
    sitemaps = []
    links = []

    # Get sitemap URLs for each day in specified period
    start = datetime.datetime.strptime(date_from, "%Y-%m-%d")
    end = datetime.datetime.today()

    all_days = [start + datetime.timedelta(days=x) for x in range(0, (end-start).days)]

    for day in all_days:
        date = day.strftime("%Y-%m-%d")
        url = "https://medium.com/sitemap/posts/{}/posts-{}.xml".format(date[:4], date)
        sitemaps.append(url)

    # Get links from all sitemaps
    for link in sitemaps:
        try:
            sm = open_url_xml(link)
            urls = sm.find_all("loc")
            links += [url.text for url in urls]
        except HTTPError:
            pass

    return links


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
    except (KeyError, AttributeError, TypeError):
        print("AttributeError, KeyError or TypeError occured.")
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


def get_posts(date_from):
    post_links = extract_post_links(date_from)

    data = {'posts': []}

    for pl in post_links:
        post_data = dict()
        post_data['url'] = pl

        try:
            post_page = open_url_html(pl)
        except (HTTPError, UnicodeError):
            print("Error occurred, skipping URL: {}".format(pl))
            continue

        post_data['title'] = extract_title(post_page, 'h1', 'graf--title')

        try:
            post_data['title'] = unicodedata.normalize('NFKD', post_data['title'])
        except TypeError:
            pass

        try:
            post_data['text'] = extract_text(post_page)
        except TypeError:
            pass

        post_data['datetime'] = extract_datetime(post_page)
        post_data['author'] = extract_author(post_page, 'a', 'ds-link', {'data-action': 'show-user-card'})
        post_data['claps'] = extract_likes(post_page, 'button', {'data-action': 'show-recommends'})

        print(post_data)

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


def main():
    get_posts(date_from="2018-07-06")


if __name__ == "main":
    main()
