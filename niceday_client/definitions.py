from enum import IntEnum, Enum

USER_PROFILE_KEYS = ['firstName', 'lastName', 'location', 'birthDate', 'gender']

class Tracker(IntEnum):
    SMOKING = 1

class TrackerName(Enum):
    SMOKING = 'tracker_smoking'
