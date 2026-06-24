"""Custom exception hierarchy for LGTM Bot."""
from __future__ import annotations


class LGTMBotError(Exception):
    """Base exception for all bot errors."""


class PRNotFound(LGTMBotError):
    def __init__(self, pr_number: int) -> None:
        self.pr_number = pr_number
        super().__init__(f"PR #{pr_number} is not in the review queue.")


class PRAlreadyExists(LGTMBotError):
    def __init__(self, pr_number: int) -> None:
        self.pr_number = pr_number
        super().__init__(f"PR #{pr_number} is already in the review queue.")


class DuplicateAssignment(LGTMBotError):
    def __init__(self, pr_number: int, username: str) -> None:
        self.pr_number = pr_number
        self.username = username
        super().__init__(f"@{username} is already reviewing PR #{pr_number}.")


class NotAReviewer(LGTMBotError):
    def __init__(self, pr_number: int, username: str) -> None:
        self.pr_number = pr_number
        self.username = username
        super().__init__(f"@{username} does not have an active review on PR #{pr_number}.")


class NoPRsAvailable(LGTMBotError):
    def __init__(self) -> None:
        super().__init__("No eligible PRs found for auto-pick.")


class GitHubAPIError(LGTMBotError):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"GitHub API error {status_code}: {message}")


class AdminRequired(LGTMBotError):
    def __init__(self) -> None:
        super().__init__("This command is restricted to admins.")
