# -*- coding: utf-8 -*-
'''
Pyste

A dead-simple pastebin, using Flask and Pygments

:copyright: (c) 2012 by Julien (jvoisin) Voisin.
:license: GPL.
'''

import sqlite3
import hashlib
import datetime

from contextlib import closing
from flask import Flask, render_template, request, g, flash, redirect, url_for

from pygments import highlight
from pygments.lexers import guess_lexer
from pygments.formatters import HtmlFormatter

DATABASE = '/tmp/pyste.db'
SECRET_KEY = 'zibzap'
DEBUG = True

app = Flask(__name__)
app.config.from_object(__name__)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'],
        detect_types=sqlite3.PARSE_DECLTYPES)

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.close()

@app.route('/', methods=['GET', 'POST'])
def index():
    ''' Main page : please enter your paste '''
    if request.method == 'POST':
        if not request.form['input']:
            flash('Please type a content to paste')
            return render_template('index.html')

        delta = datetime.timedelta(seconds=int(request.form['expiration']))
        expiration = datetime.datetime.now() + delta
        if request.form['expiration'] == '0':
            expiration = datetime.datetime(1, 1, 1)

        identifier = hashlib.sha1(request.form['input']).hexdigest()[:8]
        paste = highlight(
                    request.form['input'],
                    guess_lexer(request.form['input']),
                    HtmlFormatter(linenos='table')
                )

        g.db.execute('INSERT INTO PASTE (id, title, expiration, content) VALUES (?, ?, ?, ?)',
            (
                identifier,
                request.form['title'],
                expiration,
                paste
            )
        )
        g.db.commit()
        return render_template('index.html', identifier=identifier, url=request.url)
    return render_template('index.html')

@app.route('/<identifier>')
def show_paste(identifier):
    ''' Show the <id> paste if it exists, index instead '''
    cursor = g.db.execute('SELECT * FROM PASTE WHERE id = ?', [identifier])
    result = [dict((cursor.description[idx][0], value)
               for idx, value in enumerate(row)) for row in cursor.fetchall()]
    paste = result[0] if result else None

    try:
        if paste['expiration'] - datetime.datetime.now() < datetime.timedelta(seconds=1):
            g.db.execute('DELETE FROM PASTE WHERE id = ?', [identifier])
            g.db.commit()

            if paste['expiration'] == datetime.datetime(1, 1, 1):  # burn after reading
                flash('This paste will be burned when you close it')
                paste.pop('id')
                return render_template('paste.html', paste=paste)
            raise TypeError
    except TypeError:
        flash('No paste for id ' + identifier + '.')
        return redirect(url_for('index'))

    return render_template('paste.html', paste=paste, url=request.url)

if __name__ == '__main__':
    app.run()
