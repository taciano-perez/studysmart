from flask import Flask, render_template
import calendar
import datetime

app = Flask(__name__)

@app.route('/')
def index():
    now = datetime.date.today()
    cal = calendar.HTMLCalendar(calendar.MONDAY).formatmonth(now.year, now.month)
    return render_template('index.html', calendar_html=cal, today=now.isoformat())

if __name__ == '__main__':
    app.run(debug=True)
