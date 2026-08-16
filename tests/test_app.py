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


def test_school_year_boundary_mapping():
    boundary = app.school_year_start(2026)
    assert app.school_year_for_date(boundary - datetime.timedelta(days=1)) == 2025
    assert app.school_year_for_date(boundary) == 2026
    assert app.school_year_bounds(2026) == (
        boundary,
        datetime.date.fromisocalendar(2027, 32, 1),
    )
    _, report_end = app.school_year_bounds(2026)
    assert datetime.date.fromisocalendar(2027, 31, 7) < report_end


def test_current_school_year_selector(client):
    current_start_year = app.school_year_for_date(datetime.date.today())
    current_label = app.format_school_year(current_start_year)

    response = client.get('/')

    assert response.status_code == 200
    assert b'id="schoolYearMenu"' in response.data
    assert f'School year: {current_label}'.encode() in response.data
    assert f'>{current_label}</a>'.encode() in response.data


def test_school_year_dropdown_discovers_study_and_sleep_data(client):
    study_year = 2023
    sleep_year = 2024
    client.post(
        '/study_hours',
        data={
            'studyDate': (
                app.school_year_start(study_year) + datetime.timedelta(weeks=2)
            ).isoformat(),
            'studyLength': '30',
            'studyDesc': 'Biology',
        },
    )
    client.post(
        '/sleep_hours',
        data={
            'sleepDate': (
                app.school_year_start(sleep_year) + datetime.timedelta(weeks=2)
            ).isoformat(),
            'sleepLength': '8',
        },
    )

    response = client.get('/')

    assert app.format_school_year(study_year).encode() in response.data
    assert app.format_school_year(sleep_year).encode() in response.data


def test_reports_are_filtered_by_selected_school_year(client):
    first_year = 2023
    second_year = 2024
    client.post(
        '/study_hours',
        data={
            'studyDate': (
                app.school_year_start(first_year) + datetime.timedelta(weeks=2)
            ).isoformat(),
            'studyLength': '45',
            'studyDesc': 'Earlier subject',
        },
    )
    client.post(
        '/study_hours',
        data={
            'studyDate': (
                app.school_year_start(second_year) + datetime.timedelta(weeks=2)
            ).isoformat(),
            'studyLength': '90',
            'studyDesc': 'Later subject',
        },
    )

    selected_label = app.format_school_year(first_year)
    response = client.get(f'/?school_year={selected_label}')

    assert response.status_code == 200
    assert f'School year: {selected_label}'.encode() in response.data
    assert b'earlier subject:' in response.data
    assert b'0.75 hours' in response.data
    assert b'<strong>45 / 300</strong> mins' in response.data
    assert b'later subject:' not in response.data
    assert b'1.5 hours' not in response.data
    assert b'<strong>90 / 300</strong> mins' not in response.data


def test_reports_include_week_31_of_the_ending_year(client):
    start_year = 2023
    ending_week_date = datetime.date.fromisocalendar(start_year + 1, 31, 3)
    client.post(
        '/study_hours',
        data={
            'studyDate': ending_week_date.isoformat(),
            'studyLength': '75',
            'studyDesc': 'Summer review',
        },
    )

    response = client.get(
        f'/?school_year={app.format_school_year(start_year)}'
    )

    assert b'summer review:' in response.data
    assert b'1.25 hours' in response.data
    assert b'<strong>75 / 300</strong> mins' in response.data
    assert app.format_school_year(start_year).encode() in response.data
    assert app.format_school_year(start_year + 1).encode() in response.data


def test_month_navigation_preserves_selected_school_year(client):
    displayed_month = datetime.date.today().replace(day=1)
    displayed_month = (displayed_month - datetime.timedelta(days=1)).replace(day=1)
    previous_month = (
        displayed_month - datetime.timedelta(days=1)
    ).replace(day=1)
    selected_label = app.format_school_year(
        app.school_year_for_date(datetime.date.today()) - 1
    )

    response = client.get(
        f'/?month={displayed_month:%Y-%m}&school_year={selected_label}'
    )

    expected_query = (
        f'?month={previous_month:%Y-%m}&amp;school_year={selected_label}'
    )
    assert expected_query.encode() in response.data


def test_invalid_school_year_falls_back_to_current(client):
    current_label = app.format_school_year(
        app.school_year_for_date(datetime.date.today())
    )

    response = client.get('/?school_year=2026-2028')

    assert response.status_code == 200
    assert f'School year: {current_label}'.encode() in response.data


def test_add_study_hours(client):
    today = datetime.date.today().isoformat()
    response = client.post(
        '/study_hours',
        data={'studyDate': today, 'studyLength': '30', 'studyDesc': ' Math ', 'studyNotes': 'Reviewed algebra'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    conn = app.get_conn()
    cur = conn.cursor()
    cur.execute('SELECT study_date, num_minutes, descr, studied_parent, notes FROM STUDY_HOURS')
    rows = cur.fetchall()
    conn.close()
    assert rows == [(today, 30, 'math', 0, 'Reviewed algebra')]
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
    cur.execute('SELECT study_date, num_minutes, descr, studied_parent, notes FROM STUDY_HOURS')
    rows = cur.fetchall()
    conn.close()
    assert rows == [(today, 45, 'science', 1, None)]
    assert b'"studied_parent": true' in response.data
    assert b'study-dot-parent' in response.data


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
