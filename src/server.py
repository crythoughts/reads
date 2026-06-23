from aiohttp import web
from BooksSearch import search_books, get_book_by_id, get_book_text
from pathlib import Path
import asyncio
import logging
import aiohttp_jinja2
import jinja2

routes = web.RouteTableDef()

logging.basicConfig(
    level = logging.DEBUG
)

@routes.get('/api/books')
async def f1(request: web.Request):
    query = request.rel_url.query
    key_phrase = query.get('q', '')
    page = int(query.get('page', '0'))

    d = await search_books(q = key_phrase, page = page)

    return web.json_response(data = d)

@routes.get('/api/book')
async def f2(request: web.Request):
    query = request.rel_url.query
    ids = query.get('id')
    assert ids != None

    d = await get_book_by_id(ids = int(ids))

    return web.json_response(data = d)

@routes.get('/')
async def f3(request: web.Request):
    ctx = {}
    query = request.rel_url.query
    page = int(query.get('page', '0'))

    ctx['resp'] = None
    if query.get('q') != None and len(query.get('q')) > 0: # type: ignore
        ctx['q'] = query.get('q')
        ctx['page'] = page

        ctx['resp'] = await search_books(q = ctx['q'], page = page) # type: ignore

    return aiohttp_jinja2.render_template('search.html', request, ctx)

@routes.get('/book/{id}')
async def f5(request: web.Request):
    ctx = {}
    query = request.rel_url.query
    book = int(request.match_info.get('id')) # type: ignore

    d = await get_book_by_id(ids = int(book))

    assert len(d) > 0

    ctx['book'] = d[0]

    return aiohttp_jinja2.render_template('book.html', request, ctx)

@routes.get('/book/{id}/read')
async def f4(request: web.Request):
    ctx = {}
    query = request.rel_url.query
    book = int(request.match_info.get('id')) # type: ignore

    d = await get_book_text(ids = int(book))

    assert len(d) > 0

    ctx['text'] = d
    ctx['id'] = book

    return aiohttp_jinja2.render_template('read.html', request, ctx)

async def main():
    host = '127.0.0.1'
    port = 23030

    app = web.Application()
    aiohttp_jinja2.setup(
        app,
        loader = jinja2.FileSystemLoader(str(Path.cwd().joinpath('Web').joinpath('templates')))
    )

    app.router.add_routes(routes)
    app.router.add_static('/static/', path='./web/static', name='static')

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        host = host,
        port = port
    )

    await site.start()
    logging.info('server opened on {0}:{1}'.format(host, port))

    while True:
        await asyncio.sleep(3600)

asyncio.run(main())
