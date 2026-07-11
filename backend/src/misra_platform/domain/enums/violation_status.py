from enum import StrEnum


class ViolationStatus(StrEnum):
    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"
    SKIPPED = "skipped"
    FALSE_POSITIVE = "false_positive"
    SUPPRESSED = "suppressed"
    RESOLVED = "resolved"
