from flask import Flask, request, session, render_template, redirect, url_for, jsonify, make_response, send_from_directory
import praw
import pymongo
import json
import os
from random import randint
from classes import Subreddit, Phrase, Acronym

app = Flask('app', static_url_path='/static')
app.secret_key = 'very very secret'
app.config["UPLOAD_FOLDER"] = "./files"
app.config['MAX_CONTENT_LENGTH'] = 4*1024*1024
reddit = praw.Reddit('bot1')

client = pymongo.MongoClient(my_connection_string)
sub_db = client["acronym_bot"]["subreddit"]


def create_response_object(response, message):
    reply = {}
    if response == True:
        reply['message'] = 'Acronyms updated! :)'
        reply['update_status'] = 1

    else:
        reply['message'] = response
        reply['update_status'] = 0

    return reply


def misc_error_handler(my_function):
    def wrap(*args, **kwargs):
        try:
            return my_function(*args, **kwargs)
        except Exception as e:
            print(str(e))
            reply = {}
            reply['message'] = "An unexpected error occured. Please try again."
            reply['update_status'] = -1
            return make_response(jsonify(reply), 200)

    wrap.__name__ = my_function.__name__
    return wrap


@app.route('/download_acronyms')
@misc_error_handler
def download_acronyms():

    filename = Subreddit(session['sub']['name'], sub_db).get_acronym_file(
        app.config['UPLOAD_FOLDER'])

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/add_acronyms', methods=['POST'])
@misc_error_handler
def add_acronyms():

    if request.form.get("mode") == "file":
        file = request.files.get('add_acronym_file')
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))

        response = Subreddit(
            session['sub']['name'], sub_db).insert_acronyms(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))

        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))

    else:
        response = Subreddit(
            session['sub']['name'], sub_db).update_acronym_ff(request.form.get('acronym').strip(), request.form.get('full-form').strip())

    return make_response(jsonify(create_response_object(response, 'Acronyms updated! :)')), 200)


@app.route('/delete_acronyms', methods=['POST'])
@misc_error_handler
def delete_acronyms():

    if request.form.get("mode") == "manual":
        acronyms = request.form.get('acronym').strip()
        acronyms = [x.strip()
                    for x in acronyms.split(",") if x.strip() != '']

    else:
        file = request.files.get('delete_acronym_file')
        acronyms = [x.strip() for x in str(
            file.read(), 'utf-8').split("\n") if x.strip() != '']

    if acronyms == ['*']:
        response = Subreddit(session['sub']['name'],
                             sub_db).delete_all()

    else:
        response = Subreddit(
            session['sub']['name'], sub_db).delete_some(acronyms)

    return make_response(jsonify(create_response_object(response, 'Acronyms deleted! :)')), 200)


@app.route('/save_phrase', methods=['POST'])
@misc_error_handler
def save_phrase():

    phrase = request.form.get('phrase')

    response = Subreddit(session['sub']['name'],
                         sub_db).insert_phrase(phrase)

    if response == True:
        session['sub']['phrase'] = phrase

    return make_response(jsonify(create_response_object(response, 'Phrase updated! :)')), 200)


@app.route('/get_phrase')
@misc_error_handler
def get_phrase():

    message = {
        'phrase': session['sub']['phrase']
    }

    return make_response(jsonify(message), 200)


@app.route('/save_settings', methods=['POST'])
@misc_error_handler
def save_settings():

    settings = ['opted', 'auto', 'comment_frequency', 'comment_item']
    stuff = {}
    for setting in settings:
        if setting == 'comment_item' and 'comment_item' in stuff.keys():
            stuff[setting] = 2
        else:
            stuff[setting] = request.form.get(setting)

    for key, value in stuff.items():
        stuff[key] = int(value)

    response = Subreddit(session['sub']['name'], sub_db).update_settings(stuff)

    for key, value in stuff.items():
        session['sub'][key] = value

    session.modified = True

    return make_response(jsonify(create_response_object(response, 'Settings updated! :)')), 200)


@app.route('/get_settings')
@misc_error_handler
def get_settings():
    message = {
        'comment-on-post': True,
        'comment-on-comment': True,
        'comment-when-called': False,
        'comment-when-post': False,
        'comment-once': False,
        'comment-all': False,
        'opt-in': False,
        'opt-out-temp': False,
        'opt-out-for': False
    }

    if session['sub']['opted'] == 1:
        message['opt-in'] = True
    else:
        message['opt-out-temp'] = True

    if session['sub']['auto'] == 1:
        message['comment-when-post'] = True
    else:
        message['comment-when-called'] = True

    if session['sub']['comment_frequency'] == 0:
        message['comment-once'] = True
    else:
        message['comment-all'] = True

    if session['sub']['comment_item'] == 0:
        message['comment-on-comment'] = False
    elif session['sub']['comment_item'] == 1:
        message['comment-on-post'] = False

    return make_response(jsonify(message), 200)


@app.route('/')
@misc_error_handler
def index():
    return render_template('index.html', message='')


@app.route('/signup', methods=['POST'])
@misc_error_handler
def signup():

    mod_username = request.form.get('mod-username')
    subreddit_name = request.form.get('subreddit-name')
    password = request.form.get('password')

    otp = randint(100, 999)
    session['otp'] = otp
    session['subreddit'] = subreddit_name
    session['password'] = password

    if sub_db.find_one({'name': subreddit_name}) != None:
        return render_template('index.html', message=f'r/{subreddit_name} has already been registered here. Please sign in!')

    if mod_username in [x for x in reddit.subreddit(subreddit_name).moderator()]:
        reddit.redditor(mod_username).message(
            'OTP to sign-up for expandForMe', f'Your OTP for registering for the expandForMe bot is {otp}')
        return render_template('index.html', message="OTP sent")

    else:
        return render_template('index.html', message=f'{mod_username} is not a moderator of {subreddit_name}')


@app.route('/verify_otp', methods=['POST'])
@misc_error_handler
def verify_otp():

    submitted_otp = request.form.get('mod-otp')

    if 'otp' not in session.keys():
        return render_template('index.html', message='Please register first to do OTP verification - _ -')

    if int(submitted_otp) == int(session['otp']):
        session.pop('otp')

        session['sub'] = Subreddit(
            session['subreddit'], sub_db).insert_subreddit(session['password'])
        session['logged_in'] = True
        session.pop('subreddit')
        session.pop('password')
        return redirect(url_for('index'))

    else:
        return render_template('index.html', message='Incorrect OTP. Try again ( O _ O" )')


@app.route('/login', methods=['POST'])
@misc_error_handler
def login():

    subreddit_name = request.form.get('subreddit-name')
    password = request.form.get('password')

    sub = Subreddit(subreddit_name, sub_db).get_subreddit()

    if sub is None:
        return render_template('index.html', message=f'r/{subreddit_name} has not been registered. Sign up using an account that moderates this subreddit.')

    if password != sub['password']:
        return render_template('index.html', message='Incorrect Password. Try again :( ')
    else:
        sub.pop('acronym_list')
        session['sub'] = sub
        session['logged_in'] = True
        return redirect(url_for('index'))


@app.route('/logout')
@misc_error_handler
def logout():
    session.pop('sub')
    session['logged_in'] = False

    return redirect(url_for('index'))
