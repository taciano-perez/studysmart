import os
import sys
import datetime

# Ensure we're using SQLite database for tests
os.environ.pop('DATABASE_URL', None)

# Add project root to Python path so ``import app`` works
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import app

import pytest


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / 'test.db'
    app.DB_NAME = str(db_path)
    app.init_db()
    app.app.config['TESTING'] = True
    with app.app.test_client() as client:
        yield client


def test_index_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'StudySmart' in response.data
    assert b'<strong>0 / 300</strong> mins' in response.data
    assert b'value="30"' in response.data
    assert b'studied with a parent?' in response.data
    today = datetime.date.today()
    week_nums = [
        (today - datetime.timedelta(days=7 * i)).isocalendar()[1]
        for i in range(4)
    ]
    for num in week_nums:
        assert f"Week #{num}".encode() in response.data
    assert b'Study hours per subject' in response.data

    first_of_month = today.replace(day=1)
    prev_month = (first_of_month - datetime.timedelta(days=1)).replace(day=1)
    next_month = (first_of_month + datetime.timedelta(days=31)).replace(day=1)
    assert f"?month={prev_month.strftime('%Y-%m')}".encode() in response.data
    assert f"?month={next_month.strftime('%Y-%m')}".encode() not in response.data


def test_previous_month_navigation(client):
    today = datetime.date.today().replace(day=1)
    prev_month = (today - datetime.timedelta(days=1)).replace(day=1)
    resp = client.get(f'/?month={prev_month.strftime("%Y-%m")}')
    assert resp.status_code == 200
    # Next link should point to current month
    assert f"?month={today.strftime('%Y-%m')}".encode() in resp.data


def test_add_study_hours(client):
    today = datetime.date.today().isoformat()
    response = client.post(
        '/study_hours',
        data={'studyDate': today, 'studyLength': '30', 'studyDesc': ' Math '},
        follow_redirects=True,
    )
    assert response.status_code == 200
    conn = app.get_conn()
    cur = conn.cursor()
    cur.execute('SELECT study_date, num_minutes, descr, studied_parent FROM STUDY_HOURS')
    rows = cur.fetchall()
    conn.close()
    assert rows == [(today, 30, 'math', 0)]
    assert b'math:' in response.data
    assert b'0.5 hours' in response.data
    assert b'progress-bar' in response.data


def test_add_study_hours_with_parent(client):
    today = datetime.date.today().isoformat()
    response = client.post(
        '/study_hours',
        data={'studyDate': today, 'studyLength': '45', 'studyDesc': ' Science ', 'studiedParent': '1'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    conn = app.get_conn()
    cur = conn.cursor()
    cur.execute('SELECT study_date, num_minutes, descr, studied_parent FROM STUDY_HOURS')
    rows = cur.fetchall()
    conn.close()
    assert rows == [(today, 45, 'science', 1)]


def test_add_sleep_hours(client):
    today = datetime.date.today().isoformat()
    response = client.post(
        '/sleep_hours',
        data={'sleepDate': today, 'sleepLength': '8'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    conn = app.get_conn()
    cur = conn.cursor()
    cur.execute('SELECT date, number_hours FROM SLEEP_HOURS')
    rows = cur.fetchall()
    conn.close()
    assert rows == [(today, 8)]


def test_delete_study_entry(client):
    today = datetime.date.today().isoformat()
    client.post(
        '/study_hours',
        data={'studyDate': today, 'studyLength': '20', 'studyDesc': 'History'},
        follow_redirects=True,
    )
    conn = app.get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id FROM STUDY_HOURS')
    row_id = cur.fetchone()[0]
    conn.close()
    resp = client.post(f'/delete/study/{row_id}')
    assert resp.status_code == 204
    conn = app.get_conn()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM STUDY_HOURS')
    count = cur.fetchone()[0]
    conn.close()
    assert count == 0


def test_delete_sleep_entry(client):
    today = datetime.date.today().isoformat()
    client.post(
        '/sleep_hours',
        data={'sleepDate': today, 'sleepLength': '7'},
        follow_redirects=True,
    )
    conn = app.get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id FROM SLEEP_HOURS')
    row_id = cur.fetchone()[0]
    conn.close()
    resp = client.post(f'/delete/sleep/{row_id}')
    assert resp.status_code == 204
    conn = app.get_conn()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM SLEEP_HOURS')
    count = cur.fetchone()[0]
    conn.close()
    assert count == 0


def test_weekly_goal_marks_remaining_days_gray(client):
    today = datetime.date.today()
    week_start = today - datetime.timedelta(days=today.weekday())
    minutes = [120, 120, 60, 50]
    for offset, mins in enumerate(minutes):
        date = (week_start + datetime.timedelta(days=offset)).isoformat()
        client.post(
            '/study_hours',
            data={'studyDate': date, 'studyLength': str(mins), 'studyDesc': 'Test'},
            follow_redirects=True,
        )

    resp = client.get('/')
    html = resp.data.decode('utf-8')
    week_num = today.isocalendar()[1]
    import re
    pattern = rf"Week #{week_num}</div>\s*<div class=\"d-flex flex-grow-1 me-2\" style=\"height:20px;\">(.*?)</div>\s*<div><strong"
    match = re.search(pattern, html, re.DOTALL)
    assert match, 'Weekly progress bar not found'
    bar_html = match.group(1)
    assert 'bg-warning' not in bar_html
    assert 'bg-danger' not in bar_html
    assert 'bg-white' not in bar_html
    assert 'bg-secondary' in bar_html
