from flask import Flask, render_template, request, redirect, url_for
import calendar
import datetime
import sqlite3

DB_NAME = 'studysmart.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS STUDY_HOURS (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_date TEXT,
            num_minutes INTEGER,
            descr VARCHAR(500)
        )"""
    )
    conn.commit()
    conn.close()

init_db()

app = Flask(__name__)

@app.route('/')
def index():
    now = datetime.date.today()
    cal = calendar.HTMLCalendar(calendar.MONDAY).formatmonth(now.year, now.month)
    return render_template('index.html', calendar_html=cal, today=now.isoformat())


@app.route('/study_hours', methods=['POST'])
def study_hours():
    study_date = request.form.get('studyDate')
    num_minutes = request.form.get('studyLength')
    descr = request.form.get('studyDesc', '')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        'INSERT INTO STUDY_HOURS (study_date, num_minutes, descr) VALUES (?, ?, ?)',
        (study_date, int(num_minutes), descr[:500]),
    )
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
