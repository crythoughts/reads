from yarl import URL
from bs4 import BeautifulSoup
from pathlib import Path
from tinydb import TinyDB, Query
import aiohttp

session_timeout = aiohttp.ClientTimeout(total=None,sock_connect=10,sock_read=10)

base_url = None

if Path.cwd().joinpath('url.txt').exists():
    base_url = Path.cwd().joinpath('url.txt').read_text()
else:
    with Path.cwd().joinpath('url.txt').open('w') as f:
        f.write('https://')

assert base_url != None and len(base_url) > 0 and base_url != 'https://', 'src/url.txt is not set!'

data = Path.cwd().parent.joinpath('data')
data.mkdir(exist_ok=True)
books_cache = TinyDB(str(data.joinpath('books.json')))
texts_cache_dir = Path.cwd().parent.joinpath('texts')
texts_cache_dir.mkdir(exist_ok=True)

def split_author(name: str):
    return name.split('-')

async def search_books(q: str, page: int):
    data = None
    per_page = 20

    url = str(URL('{0}/booksearch'.format(base_url)).with_query({
        'chs': 'on',
        'cha': 'on',
        'chb': 'on',
        'ask': q,
        'page': page
    }))

    async with aiohttp.ClientSession(timeout = session_timeout) as session:
        async with session.get(url) as response:
            data = await response.text()

    bs = BeautifulSoup(data, 'html.parser')
    d = {
        'genres': [],
        'books': [],
        'authors': [],
        'sequences': [],
    }

    txts = bs.select('#main > h3')
    for txt in txts:
        t = txt.text
        ul = txt.find_next_sibling('ul')
        p: list[str] = t.split(' ')
        total_count = p[-1][:-2]
        key = None
        if 'Найденные серии' in t:
            key = 'sequences'

        if 'Найденные писатели' in t:
            key = 'authors'

        if 'Найденные книги' in t:
            key = 'books'

        for li in ul.find_all('li'): # type: ignore
            aa = li.find_all('a')
            href = li.find('a').get('href')
            title = li.find('a').text

            ids = int(href.split('/')[-1])
            f = books_cache.search(Query().id == ids)
            if len(f) > 0:
                d[key].append(f[0]) # type: ignore
                continue

            ite = {
                'url': href,
                'title': title,
                'id': ids
            }

            if key == 'books':
                if len(aa) > 1:
                    author = aa[-1]
                    lnk1 = author.get('href')
                    lnk11 = lnk1.split('/')[-1]
                    lnk2 = aa[0].text

                    ite['author'] = author.text
                    ite['author_id'] = int(lnk11)
                    ite['name'] = lnk2
                else:
                    ite['author'] = ''
                    ite['author_id'] = 0
                    ite['name'] = title

            if key != None:
                d[key].append(ite)

        d[key + '_count'] = int(total_count) # type: ignore

    if (page + 1) * per_page < d.get('books_count', 0): # type: ignore
        d['next_page'] = (page + 1) # type: ignore

    return d

async def get_book_by_id(ids: int):
    url = str(URL('{1}/b/{0}'.format(ids, base_url)))
    f = books_cache.search(Query().id == ids)
    if len(f) > 0:
        return f

    data = None
    async with aiohttp.ClientSession(timeout = session_timeout) as session:
        async with session.get(url) as response:
            data = await response.text()

    bs = BeautifulSoup(data, 'html.parser')
    title = None

    if bs.select('.title') != None:
        title = bs.select('.title')[0].text # type: ignore

    d = {
        'title': title,
        'name': title,
        'id': ids,
        'url': '/b/' + str(ids),
        'authors': [],
        'formats': []
    }

    author_texts = []
    for au in bs.select("#main a[href^='/a/']")[1:]:
        h = au.get('href')
        h1 = h.split('/') # type: ignore
        d['authors'].append({
            'id': int(h1[-1]),
            'name': au.text
        })

        author_texts.append(au.text)

    d['author'] = ', '.join(author_texts)

    if bs.select('#main img') != None:
        imgs = bs.select("#main img")[1]

        if imgs.get('src') != None:
            d['cover_url'] = base_url + imgs.get('src') # type: ignore

    for b in bs.select('.genre')[0].find_next_siblings('a'):
        hr = b.get('href') # type: ignore
        h = hr.split('/')[-1] # type: ignore

        if h in ['read', 'fb2', 'epub', 'mobi', 'pdf', 'djvu']:
            d.get('formats').append(h) # type: ignore

    books_cache.insert(d)

    return [d]

async def get_book_text(ids: int):
    cached_p = texts_cache_dir.joinpath(str(ids) + '.txt')
    if cached_p.exists():
        t = cached_p.read_text(encoding = 'utf-8')

        if len(t) > 0:
            return t

    url = str(URL('{1}/b/{0}/read'.format(ids, base_url)))

    data = None
    async with aiohttp.ClientSession(timeout = session_timeout) as session:
        async with session.get(url) as response:
            data = await response.text()

    bs = BeautifulSoup(data, 'html.parser')
    h3 = bs.select('.book')

    if h3 == None:
        return ''

    for i in bs.select('[src]'):
        src: str = i.get('src') # type: ignore

        if base_url in src:
            continue

        i['loading'] = 'lazy'
        i['src'] = base_url+src

    texts = ''

    for f in h3[0].find_next_siblings():
        texts += str(f)

    with open(str(cached_p), 'w', encoding = 'utf-8') as f:
        f.write(texts)

    return texts
