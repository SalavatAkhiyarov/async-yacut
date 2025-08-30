from http import HTTPStatus

from flask import jsonify, request, url_for

from . import app
from .models import URLMap


@app.route('/api/id/', methods=('POST',))
def create_short_link():
    if not request.is_json:
        return (
            jsonify({'message': 'Отсутствует тело запроса'}),
            HTTPStatus.BAD_REQUEST
        )
    data = request.get_json(silent=True)
    if not data:
        return (
            jsonify({'message': 'Отсутствует тело запроса'}),
            HTTPStatus.BAD_REQUEST
        )
    url = data.get('url')
    custom_id = data.get('custom_id')
    if not url:
        return (
            jsonify({'message': '"url" является обязательным полем!'}),
            HTTPStatus.BAD_REQUEST
        )
    try:
        urlmap = URLMap.create(original=url, custom_id=custom_id)
    except ValueError as e:
        return jsonify({'message': str(e)}), HTTPStatus.BAD_REQUEST
    return (
        jsonify({
            'url': urlmap.original,
            'short_link': urlmap.short_link
        }),
        HTTPStatus.CREATED,
    )


@app.route('/api/id/<string:short_id>/', methods=('GET',))
def get_original_link(short_id):
    urlmap = URLMap.get_by_short(short_id)
    if not urlmap:
        return (
            jsonify({'message': 'Указанный id не найден'}),
            HTTPStatus.NOT_FOUND
        )
    return jsonify({'url': urlmap.original}), HTTPStatus.OK
