#!/usr/bin/pytest

import json
import pytest
import threading
from unittest.mock import MagicMock
from uuid import uuid4

from cambalache.cmb_notification import notification_center, CmbNotification
from cambalache import utils
from . import utils as test_utils


DAY = 3600 * 24
now = utils.utcnow()
CMB_UUID = str(uuid4())
POLL_UUID = str(uuid4())

POLL_NOTIFICATION_BASE = {
    "type": "poll",
    "start_date": now - DAY,
    "end_date":  now + DAY,
    "poll": {
        "start_date": now - DAY,
        "end_date": now + DAY,
        "allowed_votes": 1,
        "description": "A poll to test the frontend",
        "id": POLL_UUID,
        "options": [
            "First option",
            "Second option",
            "None of the above"
        ],
        "title": "Test Poll"
    }
}


def wait_for_all_threads():
    for t in threading.enumerate():
        if t == threading.current_thread():
            continue
        t.join()


def test_cmb_notification_enabled():
    assert not notification_center.uuid
    assert notification_center.enabled is True
    notification_center.enabled = False
    assert notification_center.enabled is False
    assert len(notification_center.store) == 0
    notification_center.enabled = True


@pytest.mark.parametrize("response, headers, n", [
    (
        {
            "uuid": CMB_UUID,
            "notification": {
                "type": "version",
                "start_date": now - DAY,
                "end_date":  now + DAY,
                "version": "1.0.0",
                "release_notes": "Some Notes",
                "read_more_url": "http://localhost"
            }
        },
        {
            'User-Agent': notification_center.user_agent
        },
        1
    ),
    (
        {
            "uuid": CMB_UUID,
            "notification": {
                "type": "message",
                "start_date": now - DAY,
                "end_date":  now + DAY,
                "title": "A simple message",
                "message": "This is a message notification"
            }
        },
        {
            'User-Agent': notification_center.user_agent,
            'x-cambalache-uuid': CMB_UUID
        },
        2
    ),
    (
        {
            "uuid": CMB_UUID,
            "notification": POLL_NOTIFICATION_BASE
        },
        {
            'User-Agent': notification_center.user_agent,
            'x-cambalache-uuid': CMB_UUID
        },
        3
    ),
    (
        {
            "uuid": CMB_UUID,
            "notification": {
                **POLL_NOTIFICATION_BASE,
                "results": {
                    "total": 146,
                    "votes": [12, 56, 78]
                }
            }
        },
        {
            'User-Agent': notification_center.user_agent,
            'x-cambalache-uuid': CMB_UUID
        },
        4
    )
])
def test_cmb_notification_get(mocker, response, headers, n):
    wait_for_all_threads()

    mocker.patch(
        "http.client.HTTPSConnection.getresponse",
        return_value=MagicMock(
            status=200,
            read=MagicMock(return_value=json.dumps(response).encode())
        )
    )

    request_mock = mocker.patch("http.client.HTTPSConnection.request")

    notification_center.REQUEST_INTERVAL = 100
    notification_center.next_request = 0

    on_new_notification = MagicMock()
    notification_center.connect("new-notification", on_new_notification)

    notification_center._get_notification()

    test_utils.process_all_pending_gtk_events()

    request_mock.assert_called_with("GET", "/notification", headers=headers)

    assert notification_center.uuid == CMB_UUID
    on_new_notification.assert_called()

    assert len(notification_center.store) == n


def test_cmb_notification_get_interval(mocker):
    wait_for_all_threads()

    mocker.patch(
        "http.client.HTTPSConnection.getresponse",
        return_value=MagicMock(
            status=200,
            read=MagicMock(return_value=json.dumps({}).encode())
        )
    )

    request_mock = mocker.patch("http.client.HTTPSConnection.request")

    notification_center.REQUEST_INTERVAL = 1
    notification_center.next_request = 0

    notification_center._get_notification()

    # Test if more than one notification is called
    # First time will be called immediately and then every 1 second
    test_utils.process_all_pending_gtk_events(deciseconds=28)
    assert request_mock.call_count > 2
    assert notification_center.next_request > now

    notification_center.REQUEST_INTERVAL = 100
    notification_center.next_request = now + DAY


def test_cmb_notification_post_vote(mocker):
    wait_for_all_threads()

    poll = notification_center.store[0]
    assert isinstance(poll, CmbNotification)
    assert poll.poll.id == POLL_UUID
    assert poll.results.total == 146
    assert poll.results.votes == [12, 56, 78]

    mocker.patch(
        "http.client.HTTPSConnection.getresponse",
        return_value=MagicMock(
            status=200,
            read=MagicMock(return_value=json.dumps({
                "uuid": POLL_UUID,
                "results": {
                    "total": 1,
                    "votes": [0, 1, 0]
                }
            }).encode())
        )
    )

    request_mock = mocker.patch("http.client.HTTPSConnection.request")

    notification_center.poll_vote(poll, [1])

    test_utils.process_all_pending_gtk_events()

    request_mock.assert_called_with(
        "POST",
        f"/poll/{POLL_UUID}",
        json.dumps({"votes": [1]}),
        {
            "User-Agent": notification_center.user_agent,
            "x-cambalache-uuid": CMB_UUID,
            "Content-type": "application/json"
        }
    )

    assert poll.results.total == 1
    assert poll.results.votes == [0, 1, 0]


def test_cmb_notification_refresh_results(mocker):
    wait_for_all_threads()

    poll = notification_center.store[0]
    assert isinstance(poll, CmbNotification)
    assert poll.poll.id == POLL_UUID
    assert poll.results.total == 1
    assert poll.results.votes == [0, 1, 0]

    mocker.patch(
        "http.client.HTTPSConnection.getresponse",
        return_value=MagicMock(
            status=200,
            read=MagicMock(return_value=json.dumps({
                "uuid": POLL_UUID,
                "results": {
                    "total": 2,
                    "votes": [0, 1, 1]
                }
            }).encode())
        )
    )

    request_mock = mocker.patch("http.client.HTTPSConnection.request")

    notification_center.poll_refresh_results(poll)

    test_utils.process_all_pending_gtk_events()

    request_mock.assert_called_with(
        "GET",
        f"/poll/{POLL_UUID}",
        None,
        {
            "User-Agent": notification_center.user_agent,
            "x-cambalache-uuid": CMB_UUID,
            "Content-type": "application/json"
        }
    )

    assert poll.results.total == 2
    assert poll.results.votes == [0, 1, 1]
