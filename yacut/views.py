import asyncio
import os
import random
import string

import aiohttp
from flask import Response, abort, flash, redirect, render_template, url_for

from . import app, db
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
            data = await r.json()
    return path


def get_unique_short_id(length=6):
    if length > 16:
        raise ValueError('Максимальная длина короткой ссылки 16 символов')
    chars = string.ascii_letters + string.digits
    while True:
        short = ''.join(random.choices(chars, k=length))
        if not URLMap.query.filter_by(short=short).first():
            return short


@app.route('/', methods=('GET', 'POST'))
def index():
    form = URLForm()
    if form.validate_on_submit():
        custom_id = form.custom_id.data or get_unique_short_id()
        if (
            URLMap.query.filter_by(short=custom_id).first()
            or custom_id == 'files'
        ):
            flash('Предложенный вариант короткой ссылки уже существует.')
            return render_template('index.html', form=form)
        urlmap = URLMap(original=form.original_link.data, short=custom_id)
        db.session.add(urlmap)
        db.session.commit()
        short_link = url_for('redirect_view', short=custom_id, _external=True)
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
            short_id = get_unique_short_id()
            urlmap = URLMap(original=file_url, short=short_id)
            db.session.add(urlmap)
            short_links.append({
                'name': file.filename,
                'short': url_for(
                    'redirect_view',
                    short=short_id,
                    _external=True
                )
            })
        db.session.commit()
        return render_template(
            'files.html', form=form, short_links=short_links
        )
    return render_template('files.html', form=form)


@app.route('/<string:short>')
def redirect_view(short):
    urlmap = URLMap.query.filter_by(short=short).first_or_404()
    path = urlmap.original
    if not path.startswith('app:/'):
        return redirect(path)

    async def fetch_file(path):
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(
                f'{API_URL}/download',
                params={'path': path}
            ) as r:
                if r.status != 200:
                    return None, None
                data = await r.json()
                download_href = data.get('href')
            if not download_href:
                return None, None
            async with session.get(download_href) as r:
                if r.status != 200:
                    return None, None
                content = await r.read()
                content_type = r.headers.get('Content-Type')
                return content, content_type

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    file_data, mime_type = loop.run_until_complete(fetch_file(path))
    if not file_data:
        abort(404)
    filename = os.path.basename(path.replace('app:/', ''))
    return Response(file_data, headers={
        'Content-Disposition': f'attachment; filename={filename}',
        'Content-Type': mime_type or 'application/octet-stream'
    })
