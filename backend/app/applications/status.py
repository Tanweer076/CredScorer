from enum import StrEnum


class Status(StrEnum):
    SUBMITTED = "SUBMITTED"
    DOCS_VERIFIED = "DOCS_VERIFIED"
    SCORED = "SCORED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


ALLOWED_TRANSITIONS: dict[Status, set[Status]] = {
    Status.SUBMITTED: {Status.DOCS_VERIFIED},
    Status.DOCS_VERIFIED: {Status.SCORED},
    Status.SCORED: {Status.APPROVED, Status.REJECTED, Status.MANUAL_REVIEW},
    Status.MANUAL_REVIEW: {Status.APPROVED, Status.REJECTED},
}


class IllegalTransition(ValueError):
    pass


def check_transition(current: str, new: str) -> Status:
    """Raise IllegalTransition unless current -> new is allowed by the status flow."""
    current, new = Status(current), Status(new)
    if new not in ALLOWED_TRANSITIONS.get(current, set()):
        raise IllegalTransition(f"Cannot move application from {current} to {new}")
    return new