from enum import StrEnum


class Environment(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    CI = "ci"
    TEST = "test"
