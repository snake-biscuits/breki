from __future__ import annotations
import re
from typing import List


class TokenClass:
    """helper class for text <-> object conversion"""
    pattern: re.Pattern  # compiled regex w/ groups

    def __str__(self) -> str:
        raise NotImplementedError()

    @classmethod
    def from_string(cls, string: str) -> TokenClass:
        match = cls.pattern.match(string)
        assert match is not None
        return cls.from_tokens(match.groups())

    @classmethod
    def from_tokens(cls, tokens: List[str]) -> TokenClass:
        raise NotImplementedError()
