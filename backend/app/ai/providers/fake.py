"""Offline provider placeholder used by default in development and tests."""


class FakeProvider:
    """A deliberately non-clinical placeholder; Phase 7 defines its safe schema."""

    provider_name = "fake"

    def is_available(self) -> bool:
        return True
