import asyncio
import os
from http import HTTPStatus

import aiohttp
from flask import Response, abort, flash, redirect, render_template, url_for

from . import app
from .forms import FileForm, URLForm
from .models import URLMap

API_URL = 'https://cloud-api.yandex.net/v1/disk/resources'
HEADERS = {'Authorization': f'OAuth {app.config["DISK_TOKEN"]}'}


async def upload_to_yandex_async(file_storage):
    filename = file_storage.filename
    path = f'app:/{filename}'
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(
            f'{API_URL}/upload',
            params={'path': path, 'overwrite': 'true'}
        ) as r:
            if r.status != HTTPStatus.OK:
                return None
            data = await r.json()
            href = data.get('href')
            if not href:
                return None
        file_storage.stream.seek(0)
        file_bytes = file_storage.read()
        async with session.put(href, data=file_bytes):
            pass
        async with session.get(
            f'{API_URL}/download',
            params={'path': path}
        ) as r:
            if r.status != HTTPStatus.OK:
                return None
            await r.json()
    return path


@app.route('/', methods=('GET', 'POST'))
def index():
    form = URLForm()
    if form.validate_on_submit():
        try:
            urlmap = URLMap.create(
                original=form.original_link.data,
                custom_id=form.custom_id.data
            )
        except ValueError as e:
            flash(str(e))
            return render_template('index.html', form=form)
        short_link = url_for(
            'redirect_view', short=urlmap.short, _external=True
        )
        flash(f'Ваша новая ссылка: {short_link}')
        return render_template('index.html', form=form, short_link=short_link)
    return render_template('index.html', form=form)


@app.route('/files', methods=('GET', 'POST'))
def files():
    form = FileForm()
    if form.validate_on_submit():
        short_links = []
        for file in form.files.data:
            file_url = asyncio.run(upload_to_yandex_async(file))
            if not file_url:
                flash(f'Ошибка загрузки файла {file.filename}')
                continue
            try:
                urlmap = URLMap.create(original=file_url)
            except ValueError as e:
                flash(str(e))
                continue
            short_links.append({
                'name': file.filename,
                'short': url_for(
                    'redirect_view',
                    short=urlmap.short,
                    _external=True
                )
            })
        return render_template(
            'files.html', form=form, short_links=short_links
        )
    return render_template('files.html', form=form)


@app.route('/<string:short>')
def redirect_view(short):
    urlmap = URLMap.get_by_short(short)
    if not urlmap:
        abort(HTTPStatus.NOT_FOUND)
    path = urlmap.original
    if not path.startswith('app:/'):
        return redirect(path)

    async def fetch_file(path):
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(
                f'{API_URL}/download',
                params={'path': path}
            ) as r:
                if r.status != HTTPStatus.OK:
                    return None, None
                data = await r.json()
                download_href = data.get('href')
            if not download_href:
                return None, None
            async with session.get(download_href) as r:
                if r.status != HTTPStatus.OK:
                    return None, None
                content = await r.read()
                content_type = r.headers.get('Content-Type')
                return content, content_type

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    file_data, mime_type = loop.run_until_complete(fetch_file(path))
    if not file_data:
        abort(HTTPStatus.NOT_FOUND)
    filename = os.path.basename(path.replace('app:/', ''))
    return Response(
        file_data,
        headers={
            'Content-Disposition': f'attachment; filename={filename}',
            'Content-Type': mime_type or 'application/octet-stream'
        }
    )
