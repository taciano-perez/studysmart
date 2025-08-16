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


def test_add_study_hours(client):
    today = datetime.date.today().isoformat()
    response = client.post(
        '/study_hours',
        data={'studyDate': today, 'studyLength': '30', 'studyDesc': 'Math'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    conn = app.get_conn()
    cur = conn.cursor()
    cur.execute('SELECT study_date, num_minutes, descr FROM STUDY_HOURS')
    rows = cur.fetchall()
    conn.close()
    assert rows == [(today, 30, 'Math')]


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
