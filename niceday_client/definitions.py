from enum import Enum

USER_PROFILE_KEYS = ['firstName', 'lastName', 'location', 'birthDate', 'gender']


class Tracker(Enum):
    SMOKING = (1, 'tracker_smoking')
