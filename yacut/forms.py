from flask_wtf import FlaskForm
from wtforms import MultipleFileField, StringField, SubmitField
from wtforms.validators import URL, DataRequired, Length, Optional, Regexp

from .constants import MAX_ORIGINAL_LENGTH, MAX_SHORT_LENGTH, VALID_SHORT_RE


class URLForm(FlaskForm):
    original_link = StringField(
        'Длинная ссылка',
        validators=(
            DataRequired(message='Укажите ссылку'),
            URL(message='Введите корректный URL'),
            Length(max=MAX_ORIGINAL_LENGTH, message='Ссылка слишком длинная')
        )
    )
    custom_id = StringField(
        'Ваш вариант короткой ссылки',
        validators=(
            Length(
                max=MAX_SHORT_LENGTH,
                message=f'Максимум {MAX_SHORT_LENGTH} символов'
            ),
            Regexp(
                VALID_SHORT_RE, message='Только латинские буквы и цифры'
            ),
            Optional()
        )
    )
    submit = SubmitField('Создать')


class FileForm(FlaskForm):
    files = MultipleFileField(
        'Выберите файлы',
        validators=(DataRequired(message='Файл не выбран'),)
    )
    submit = SubmitField('Загрузить')
