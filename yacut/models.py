import random
import string
from datetime import datetime

from flask import url_for

from . import db
from .constants import (DEFAULT_SHORT_LENGTH, MAX_GENERATION_ATTEMPTS,
                        MAX_ORIGINAL_LENGTH, MAX_SHORT_LENGTH, VALID_SHORT_RE)
from .exceptions import ShortIdGenerationError


class URLMap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original = db.Column(db.String(MAX_ORIGINAL_LENGTH), nullable=False)
    short = db.Column(db.String(MAX_SHORT_LENGTH), unique=True, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def generate_unique_short_id(length=DEFAULT_SHORT_LENGTH):
        if length > MAX_SHORT_LENGTH:
            raise ValueError(
                f'Максимальная длина короткой ссылки '
                f'{MAX_SHORT_LENGTH} символов'
            )
        chars = string.ascii_letters + string.digits
        for _ in range(MAX_GENERATION_ATTEMPTS):
            short = ''.join(random.choices(chars, k=length))
            if not URLMap.query.filter_by(short=short).first():
                return short
        raise ShortIdGenerationError(
            'Не удалось сгенерировать уникальный short_id'
        )

    @staticmethod
    def create(original, custom_id=None):
        if custom_id:
            if (
                not VALID_SHORT_RE.match(custom_id)
                or len(custom_id) > MAX_SHORT_LENGTH
            ):
                raise ValueError(
                    'Указано недопустимое имя для короткой ссылки'
                )
            if (
                custom_id == 'files'
                or URLMap.query.filter_by(short=custom_id).first()
            ):
                raise ValueError(
                    'Предложенный вариант короткой ссылки уже существует.'
                )
            short = custom_id
        else:
            short = URLMap.generate_unique_short_id()
        urlmap = URLMap(original=original, short=short)
        db.session.add(urlmap)
        db.session.commit()
        return urlmap

    @staticmethod
    def get_by_short(short_id):
        return URLMap.query.filter_by(short=short_id).first()

    @staticmethod
    def get_by_short_or_404(short_id):
        return URLMap.query.filter_by(short=short_id).first_or_404()

    @property
    def short_link(self):
        return url_for('redirect_view', short=self.short, _external=True)
