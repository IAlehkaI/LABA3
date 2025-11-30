# app/core/roles.py

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"
    ANONYMOUS = "anonymous"