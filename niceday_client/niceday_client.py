import typing
from dataclasses import dataclass
import datetime
from dateutil.rrule import rrule
import json
import requests

from .definitions import USER_PROFILE_KEYS


@dataclass
class TrackerStatus:
    """
    Status of a user tracker.

    Attributes:
        trackerId: ID of the the tracker (see
            https://github.com/senseobservationsystems/goalie-js/issues/840
            on how to get tracker IDs, for example: cigarette counter has id=1).
            Use the Tracker enum defined in definitions.py instead of hardcoding
            integer values. e.g. 'Tracker.SMOKING' may be used instead of 1.
        isEnabled: Whether the tracker should be enabled
    """
    trackerId: int
    isEnabled: bool


class NicedayClient:
    """
    Client for interacting with the niceday-api component of the PerfectFit
    stack.
    """

    def __init__(self, niceday_api_uri='http://localhost:8080/'):
        """
        Construct a client for interacting with the given niceday API URI.
        By default, this is assumed to be on http://localhost:8080/, but
        can be set with the niceday_api_uri parameter.
        """

        self._niceday_api_uri = niceday_api_uri

    def _call_api(self,
                  method: str,
                  url: str,
                  query_params: typing.Optional[dict] = None,
                  body: typing.Optional[dict] = None) -> requests.Response:
        """
        Handles http requests with the niceday-api.

        Args:
            method: (str) Which HTTP method to use
            url: (str) Specifies the desired url e.g. 'profiles' or 'messages'
            query_params: (dict) Parameters that should go in the query string of the request URL
            body: (dict) Body to send with request
        """

        headers = {"Accept": "application/json"}
        if query_params is None:
            query_params = {}

        if method == 'GET':
            r = requests.get(url, params=query_params, headers=headers)
        elif method == 'POST':
            r = requests.post(url, params=query_params, headers=headers, json=body)
        else:
            raise NotImplementedError('Other methods are not implemented yet')
        r.raise_for_status()
        return r

    def _extract_json(self, response: requests.Response) -> dict:
        try:
            results = response.json()
        except ValueError as e:
            raise ValueError('The niceday-api did not return JSON.') from e

        self._error_check(results, 'Unauthorized error')
        self._error_check(results, 'The requested resource could not be found')
        return results

    def _error_check(self, results, err_msg):
        if 'message' in results and err_msg in results['message']:
            msg = f"'{err_msg}' response from niceday server. "
            if 'details' in results and 'body' in results['details']:
                msg += 'Details provided: ' + str(results['details']['body'])
            raise RuntimeError(msg)

    def _get_raw_user_data(self, user_id) -> dict:
        """
        Returns the niceday user data corresponding to the given user id.
        This is in the form of a dict, containing the user's
            'networks' (memberId, role etc)
            'userProfile' (name, location, bio, birthdate etc)
            'user' info (username, email, date joined etc.)
        The exact contents of this returned data depends on what is stored
        on the SenseServer and generally could change (beyond our control).
        """
        url = self._niceday_api_uri + 'userdata/' + str(user_id)
        response = self._call_api('GET', url)
        return self._extract_json(response)

    def get_profile(self, user_id) -> dict:
        """
        Returns the niceday user profile corresponding to the given user id.
        This is in the form of dict, containing the following keys:
            'networks' (memberId, role etc)
            'userProfile' (name, location, bio, birthdate etc)
            'user' info (username, email, date joined etc.)
        The exact contents of this returned data depends on what is stored
        on the SenseServer.
        """

        user_data = self._get_raw_user_data(user_id)
        if 'userProfile' not in user_data:
            raise ValueError('NicedayClient expected user data from '
                             'niceday-api to contain the key "userProfile" '
                             'but this is missing. Has the data structure '
                             'stored on the Senseserver changed?')

        return_profile = {}
        for k in USER_PROFILE_KEYS:
            if k not in user_data['userProfile']:
                raise ValueError(f'"userProfile" dict returned from '
                                 f'niceday-api does not contain expected '
                                 f'key "{k}". Has the data structure '
                                 f'stored on the Senseserver changed?')
            return_profile[k] = user_data['userProfile'][k]

        return return_profile

    def post_message(self, recipient_id: int, text: str):
        """
        Post a message to the niceday server.

        Args:
            recipient_id: user id of the recipient
            text: text message to send

        """
        url = self._niceday_api_uri + 'messages/'
        body = {
            "recipient_id": recipient_id,
            "text": text
        }
        return self._call_api('POST', url, body=body)

    def set_user_tracker_statuses(self, user_id: int, tracker_statuses: typing.List[TrackerStatus]):
        """
        Set tracker statuses for a specific user.

        Example Usage:
            ```
            self.set_user_tracker_statuses(12345, [TrackerStatus(trackerId=Tracker.SMOKING, isEnabled=True)])

        Args:
            user_id: ID of the user we want to set tracker statuses for
            tracker_statuses: List of TrackerStatus objects.
        """
        url = self._niceday_api_uri + 'usertrackers/statuses'
        body = {
            "userId": user_id,
            "trackerStatuses": [ts.__dict__ for ts in tracker_statuses]
        }
        return self._call_api('POST', url, body=body)

    def get_smoking_tracker(self, user_id: int, start_time: datetime.datetime,
                            end_time: datetime.datetime):
        """
        Get smoking tracker data for specific user

        Args:
            user_id: ID of the user we want to set tracker statuses for
            start_time: The start of the time range for which to get data
            end_time: The end of the time range for which to get data

        Returns:
            A list of smoking tracker entries, each entry is a dict containing
            amongst others the startTime & endTime, value (which is itself a dict
            containing the key 'quantity' that depicts the number of cigarettes smoked
            in an entry).

        """
        url = self._niceday_api_uri + 'usertrackers/smoking/' + str(user_id)
        query_params = {'startTime': start_time.isoformat() + 'Z',
                        'endTime': end_time.isoformat() + 'Z'}
        query_response = self._call_api('GET', url, query_params=query_params)
        # convert the json response into a list of dict
        response_json = json.loads(query_response.content)
        return response_json

    def set_tracker_reminder(self, user_id: int, tracker_name: str, reminder_title: str, recurrence_rule: rrule):
        """
        Set tracker reminder for a specific user.

        Example Usage:
            ```
            client.set_tracker_reminder(12345, TrackerName.SMOKING.value, "This is a tracker", rrule(DAILY,dtstart=datetime.datetime(2022, 5, 12, 0, 0),until=datetime.datetime(2022, 5, 13, 0, 0)))

        Args:
            user_id: ID of the user we want to set tracker statuses for
            tracker_name: Name of the tracker to set the reminder for (see
            https://github.com/senseobservationsystems/goalie-js/issues/840
            on how to get tracker name, for example: smoking tracker has name=tracker_smoking).
            Use the TrackerName enum defined in definitions.py instead of hardcoding
            string values. e.g. 'TrackerName.SMOKING' may be used instead of 'tracker_smoking'.
            reminder_title: title of the reminder. This is displayed in the app
            recurrence_rule: rule for recursion setting. Use the rrule module to create the rule.
        """
        url = self._niceday_api_uri + 'usertrackers/reminder'

        recurring_schedule = {
            "title": reminder_title,
            "schedule_type": tracker_name,
            "recurring_expression": {
                "margin": {
                    "before": 0,
                    "after": 60
                },
                "reminder_enabled": True,
                "reminder_margin": [
                    {
                        "before": 0,
                        "after": 60
                    }
                ],
                "rrule": str(recurrence_rule)
            }
        }
        body = {
            "userId": str(user_id),
            "recurringSchedule": recurring_schedule
        }
        return self._call_api('POST', url, body=body)