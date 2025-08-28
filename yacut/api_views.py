import re

from flask import jsonify, request, url_for

from . import app, db
from .models import URLMap
from .views import get_unique_short_id

VALID_SHORT_RE = re.compile(r'^[A-Za-z0-9]+$')


@app.route('/api/id/', methods=('POST',))
def create_short_link():
    if not request.is_json:
        return jsonify({'message': 'Отсутствует тело запроса'}), 400
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'message': 'Отсутствует тело запроса'}), 400
    url = data.get('url')
    custom_id = data.get('custom_id')
    if not url:
        return jsonify({'message': '"url" является обязательным полем!'}), 400
    if custom_id:
        if not VALID_SHORT_RE.match(custom_id) or len(custom_id) > 16:
            return jsonify(
                {'message': 'Указано недопустимое имя для короткой ссылки'}
            ), 400
        if (
            custom_id == 'files'
            or URLMap.query.filter_by(short=custom_id).first()
        ):
            return jsonify(
                {
                    'message': (
                        'Предложенный вариант короткой ссылки уже существует.'
                    )
                }
            ), 400
        short = custom_id
    else:
        short = get_unique_short_id()
    urlmap = URLMap(original=url, short=short)
    db.session.add(urlmap)
    db.session.commit()
    return jsonify({
        'url': url,
        'short_link': url_for('redirect_view', short=short, _external=True)
    }), 201


@app.route('/api/id/<string:short_id>/', methods=('GET',))
def get_original_link(short_id):
    urlmap = URLMap.query.filter_by(short=short_id).first()
    if not urlmap:
        return jsonify({'message': 'Указанный id не найден'}), 404
    return jsonify({'url': urlmap.original}), 200
