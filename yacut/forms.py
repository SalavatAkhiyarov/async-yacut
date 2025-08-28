from flask_wtf import FlaskForm
from wtforms import MultipleFileField, StringField, SubmitField
from wtforms.validators import URL, DataRequired, Length, Optional, Regexp


class URLForm(FlaskForm):
    original_link = StringField(
        'Длинная ссылка',
        validators=(
            DataRequired(message='Укажите ссылку'),
            URL(message='Введите корректный URL'),
            Length(max=2048, message='Ссылка слишком длинная')
        )
    )
    custom_id = StringField(
        'Ваш вариант короткой ссылки',
        validators=(
            Length(max=16, message='Максимум 16 символов'),
            Regexp(
                r'^[a-zA-Z0-9]+$', message='Только латинские буквы и цифры'
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
