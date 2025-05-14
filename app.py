from flask import Flask, render_template, redirect, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, login_manager
import locale
import sqlite3
import hashlib
import string
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import requests
from browser_utils import advanced_words_creator
from adds import *


# from flask_restful import Api
app = Flask(__name__)

alphabet = string.ascii_letters + string.digits

app.secret_key = '485faa163da7b4529a6b10f1e4ac0f86db412a669e3d30beb475851e43acf7e2'
login_manager.session_protection = "basic"

MAIL = 'regisflow@mail.ru'
PASSWORD = "NiffyDAdwKvMfZtz3ECB"


BAD_EMAIL = 8
SUCCESS = 200


jinja_options = app.jinja_options.copy()
jinja_options.update(dict(
    block_start_string='<%',
    block_end_string='%>',
    variable_start_string='{{',
    variable_end_string='}}',
    comment_start_string='<#',
    comment_end_string='#>',
))
app.jinja_options = jinja_options
login_manager = LoginManager(app)

conn = sqlite3.connect('main.db', check_same_thread=False)
conn.isolation_level = None


class User:
    def create(self, user_id:str):
        self.id = int(user_id)
        self.email = ''
        with conn:
            cursor = conn.cursor()
            email = cursor.execute(GET_EMAIL, (user_id,)).fetchone()
        if email:
            self.email = email[0]
            return self
        return None

    def get_id(self):
        return str(self.id)

    def is_authenticated(self):
        if self.email:
            return True
        return False

    def is_active(self):
        return True

    def is_anonymous(self):
        return False


def remove_spaces(text):
    return re.sub(r'^\s+|\s+$', '', text)


def password_generator(length: int = 12):
    password = ''.join(secrets.choice(alphabet) for j in range(length))
    return password


def password_hasher(password:str):
    hashed_password = hashlib.sha256()
    hashed_password.update(bytes(password.encode()))
    hashed_password = hashed_password.hexdigest()
    return hashed_password


def mail_user(email: str, password:str, is_tmp=False):
    s = smtplib.SMTP_SSL(host='smtp.mail.ru', port=465)
    s.login(MAIL, PASSWORD)
    msg = MIMEMultipart()
    msg['From'] = MAIL
    msg['To'] = email
    if is_tmp:
        msg['Subject'] = f"Восстановление пароля на LegisFlow"
    else:
        msg['Subject'] = f"Регистрация пользователя на LegisFlow"
    body = f"Ваш пароль: {password}\nВы можете сменить его в личном кабинете"
    msg.attach(MIMEText(body, 'plain'))
    try:
        s.send_message(msg)
    except smtplib.SMTPRecipientsRefused:
        return BAD_EMAIL
    return SUCCESS


@app.route('/')
def startup():
    if current_user.is_authenticated:
        return redirect('/home')
    else:
        return render_template('startup.html')


@app.route('/home')
@login_required
def home_handler():
    with conn:
        cursor = conn.cursor()
        name = cursor.execute(GET_NAME, (current_user.id, )).fetchone()[0]
    return render_template('main_page.html', name=name)


@app.route('/profile', methods=["GET", "POST"])
@login_required
def profile_handler():
    user_id = int(current_user.id)
    with conn:
        cursor = conn.cursor()
        email, name, hashed_password = cursor.execute(GET_USER_DATA, (user_id, )).fetchone()
    if request.method == "POST":
        if request.form.get('newname'):
            new_name = request.form.get('newname')
            with conn:
                cursor = conn.cursor()
                cursor.execute(SET_NEW_NAME, (new_name, user_id))
            name = new_name

        elif request.form.get('newemail') and request.form.get('password'):
            if hashed_password == password_hasher(request.form.get('password')):
                new_email = request.form.get('newemail')
                with conn:
                    cursor = conn.cursor()
                    cursor.execute(SET_NEW_EMAIL, (new_email, user_id))
                email = new_email

        elif request.form.get('oldpassword') and request.form.get('newpassword') and request.form.get('newpassword_repeat'):
            new_password = request.form.get('newpassword')
            if new_password == request.form.get('newpassword_repeat'):
                new_hashed = password_hasher(new_password)
                old_hashed = password_hasher(request.form.get('oldpassword'))
                if hashed_password == old_hashed:
                    with conn:
                        cursor = conn.cursor()
                        cursor.execute(SET_NEW_PASSWORD, (new_hashed, user_id))
    tg_id = cursor.execute(GET_TG_ID, (user_id, )).fetchone()[0]

    if tg_id is not None:
        tg_id = "Ваш ID: " + str(tg_id)
    else:
        token = cursor.execute(GET_TOKEN, (user_id, )).fetchone()[0]
        tg_id = f"TG не привязан, ваш токен: {token}"
    return render_template('profile.html', name=name, email=email, tg_id=tg_id)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')


@login_manager.unauthorized_handler
def unauthorized():
    return redirect('/')


@app.route('/login', methods=["GET", "POST"])
def login_handler():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        if password is None:
            with conn:
                cursor = conn.cursor()
                user_id = cursor.execute(GET_USER_BY_EMAIL, (email, )).fetchone()
            if user_id:
                user_id = user_id[0]
                tmp_password = password_generator()
                hashed_tmp = password_hasher(tmp_password)
                with conn:
                    cursor = conn.cursor()
                    cursor.execute(SET_TEMP_PASSWORD, (hashed_tmp, user_id))
                mail_user(email, tmp_password, True)
            return redirect('/login')

        hashed_password = password_hasher(password)
        with conn:
            cursor = conn.cursor()
            user_id = cursor.execute(GET_USER_ID, (email, hashed_password)).fetchone()

        if user_id:
            user_id = user_id[0]
            with conn:
                cursor = conn.cursor()
                check = cursor.execute(CHECK_FOR_TEMP, (user_id,)).fetchone()
            if check:
                with conn:
                    cursor = conn.cursor()
                    cursor.execute(SET_TEMP_PASSWORD, (None, user_id))
            login_user(User().create(user_id), remember=True)
            return redirect('/')
        else:
            if password is not None:
                with conn:
                    cursor = conn.cursor()
                    user_id = cursor.execute(GET_USER_BY_TEMP, (email, hashed_password)).fetchone()
                if user_id:
                    user_id = user_id[0]
                    with conn:
                        cursor = conn.cursor()
                        cursor.execute(CHANGE_PASSWORD, (hashed_password, user_id))
                        cursor.execute(SET_TEMP_PASSWORD, (None, user_id))
                    login_user(User().create(user_id), remember=True)
                    return redirect('/')

    return render_template('login.html')


@app.route('/register', methods=["GET", "POST"])
def register_handler():
    if request.method == "POST":
        email = request.form.get('email')
        name = request.form.get('name')
        with conn:
            cursor = conn.cursor()
            check_existence = cursor.execute(CHECK_MAIL, (email, )).fetchone()
        if check_existence:
            print('Эта почта уже зарегистрирована')
            return render_template('register.html')
        password = password_generator()

        hashed_password = password_hasher(password)
        if mail_user(email, password) == SUCCESS:
            print('Успешная регистрация')
        else:
            print('email не существует')

        token = password_generator(48)
        with conn:
            cursor = conn.cursor()
            cursor.execute(CREATE_USER, (email, email, hashed_password, name, token))

        return redirect('/login')
    return render_template('register.html')


@app.route('/keywords_all')
@login_required
def keywords_all_handler():
    user_id = current_user.id
    if 'list_id' in request.args:
        list_id = int(request.args.get('list_id'))
        with conn:
            cursor = conn.cursor()
            check = cursor.execute(CHECK_SUB, (user_id, list_id)).fetchone()
        if not check:
            with conn:
                cursor = conn.cursor()
                cursor.execute(ADD_SUBSCRIPTION, (1, user_id, list_id))

    with conn:
        cursor = conn.cursor()
        name = cursor.execute(GET_NAME, (user_id, )).fetchone()[0]
    return render_template('words_all.html', name=name)


@app.route('/keywords_personal', methods=["GET", "POST"])
@login_required
def keywords_personal_handler():
    user_id = current_user.id
    if request.method == "POST":
        if 'list_id' in request.form.keys():  # edit list
            new_name = request.form.get('list_name')
            list_words = request.form.get('list_words')
            list_id = request.form.get('list_id')
            enabled = request.form.get('enabled')

            if enabled is not None:
                enabled = 1
            else:
                enabled = 0
            list_words = [remove_spaces(word) for word in list_words.split(',')]
            list_id = int(list_id)
            new_name = remove_spaces(new_name)
            with conn:
                cursor = conn.cursor()
                creator_id, old_name, public = cursor.execute(GET_LIST_INFO_BY_ID, (list_id, )).fetchone()
            if user_id == creator_id and not public:
                new_words = advanced_words_creator(list_words, cursor)
                check = False
                if new_name != old_name:
                    with conn:
                        cursor = conn.cursor()
                        check = cursor.execute(GET_LIST_ID_BY_INFO, (user_id, new_name)).fetchone()

                if not check:
                    with conn:
                        cursor = conn.cursor()
                        old_words = [item[0] for item in cursor.execute(GET_LIST_CONNECTIONS_WORDS, (list_id, )).fetchall()]
                    for word_id in old_words:
                        if word_id not in new_words:
                            with conn:
                                cursor = conn.cursor()
                                cursor.execute(DELETE_LIST_CONNECTION, (list_id, word_id))

                    for word_id in new_words:
                        if word_id not in old_words:
                            with conn:
                                cursor = conn.cursor()
                                cursor.execute(CREATE_LIST_CONNECTION, (list_id, word_id))
                    with conn:
                        cursor = conn.cursor()
                        cursor.execute(UPDATE_LIST_NAME, (new_name, list_id))
            with conn:
                cursor = conn.cursor()
                cursor.execute(UPDATE_SUBSCRIPTION, (enabled, user_id, list_id))

        else:
            new_name = request.form.get('list_name')
            list_words = request.form.get('list_words')
            enabled = request.form.get('enabled')
            if enabled is not None:
                enabled = 1
            else:
                enabled = 0
            list_words = [remove_spaces(word) for word in list_words.split(',')]
            with conn:
                cursor = conn.cursor()
                check = cursor.execute(GET_LIST_ID_BY_INFO, (user_id, new_name)).fetchone()
            if not check:
                with conn:
                    cursor = conn.cursor()
                    cursor.execute(CREATE_LIST, (user_id, new_name))
                    list_id = cursor.execute(GET_LIST_ID_BY_INFO, (user_id, new_name)).fetchone()[0]
                new_words = advanced_words_creator(list_words, cursor)
                for word_id in new_words:
                    with conn:
                        cursor = conn.cursor()
                        cursor.execute(CREATE_LIST_CONNECTION, (list_id, word_id))
                with conn:
                    cursor = conn.cursor()
                    cursor.execute(ADD_SUBSCRIPTION, (enabled, user_id,list_id))
            else:
                list_id = check[0]
                with conn:
                    cursor = conn.cursor()
                    cursor.execute(ADD_SUBSCRIPTION, (enabled, user_id,list_id))
    else:
        if 'list_id' in request.args:
            list_id = int(request.args.get('list_id'))
            user_id = current_user.id
            with conn:
                cursor = conn.cursor()
                cursor.execute(FLIP_ENABLED, (user_id, list_id))
    with conn:
        cursor = conn.cursor()
        name = cursor.execute(GET_NAME, (user_id, )).fetchone()[0]
    return render_template('words_personal.html', name=name)


@app.route('/fetch_user_lists', methods=["GET", "POST"])
@login_required
def fetch_user_lists():
    user_id = current_user.id
    with conn:
        cursor = conn.cursor()
        lists_info = cursor.execute(GET_SUBBED_IDS, (user_id,)).fetchall()
    return lists_info


@app.route('/projects_connections_json', methods=["GET", "POST"])
@login_required
def projects_connections_json():
    user_id = current_user.id
    if 'list_id' in request.args:
        list_id = int(request.args.get('list_id'))
        print(list_id)
        if list_id == -1:
            return []
    else:
        return []
    res = []
    with conn:
        cursor = conn.cursor()
        connections = cursor.execute(CONNECTIONS_BY_LIST_ID, (list_id, )).fetchall()
    project_id = -1
    words = []
    counter = -1
    for connection in connections:
        if connection[0] == project_id:
            res[counter]['keywords'].append(connection[1])
        else:
            project_id = connection[0]
            date, link, title, shortened_text, project_type = cursor.execute(PROJECT_INFO_BY_ID, (project_id, )).fetchone()
            real_id = format_id(project_id, project_type)

            res.append({'date': date, 'url': link, 'number': real_id, 'title': title, 'description': shortened_text, 'keywords': [connection[1]]})
            counter += 1

    return res


@app.route('/notifications', methods=["GET"])
@login_required
def notifications_handler():
    ...


@app.route('/public_keywords_json', methods=["GET", "POST"])
@login_required
def public_keywords_json_handler():
    if 'subbed' in request.args:
        subbed = int(request.args.get('subbed'))
        if subbed not in (0, 1):
            return False
    else:
        subbed = 1
    user_id = current_user.id
    res = []
    list_id = -1
    counter = -1
    if subbed:
        with conn:
            cursor = conn.cursor()
            search = cursor.execute(GET_LISTS_INFO_SUBBED, (user_id,)).fetchall()
        for item in search:
            if item[0] == list_id:
                res[counter]['words'].append(item[2])
            else:
                list_id = item[0]
                res.append({'name': item[1], 'words': [item[2]], 'enabled': item[3], 'list_id': list_id})
                counter += 1
    else:
        with conn:
            cursor = conn.cursor()
            search = cursor.execute(GET_LISTS_PUBLIC_UNSUBBED, (user_id,)).fetchall()
        for item in search:
            if item[0] == list_id:
                res[counter]['words'].append(item[2])
            else:
                list_id = item[0]
                res.append({'name': item[1], 'words': [item[2]], 'list_id': list_id})
                counter += 1
    return res


@login_manager.user_loader
def load_user(user_id):
    return User().create(user_id)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
