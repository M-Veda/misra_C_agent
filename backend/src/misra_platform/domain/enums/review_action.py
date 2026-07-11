from enum import StrEnum

from misra_platform.domain.enums.violation_status import ViolationStatus


class ReviewAction(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    EDIT = "edit"
    SKIP = "skip"
    FALSE_POSITIVE = "false_positive"
    SUPPRESS = "suppress"


class PatchStatus(StrEnum):
    GENERATED = "generated"
    EXPORTED = "exported"


ACTION_TO_STATUS: dict[ReviewAction, ViolationStatus] = {
    ReviewAction.ACCEPT: ViolationStatus.ACCEPTED,
    ReviewAction.REJECT: ViolationStatus.REJECTED,
    ReviewAction.EDIT: ViolationStatus.EDITED,
    ReviewAction.SKIP: ViolationStatus.SKIPPED,
    ReviewAction.FALSE_POSITIVE: ViolationStatus.FALSE_POSITIVE,
    ReviewAction.SUPPRESS: ViolationStatus.SUPPRESSED,
}

ACTIONS_REQUIRING_JUSTIFICATION: frozenset[ReviewAction] = frozenset(
    {ReviewAction.ACCEPT, ReviewAction.SUPPRESS, ReviewAction.FALSE_POSITIVE}
)

ACTIONS_GENERATING_PATCHES: frozenset[ReviewAction] = frozenset(
    {ReviewAction.ACCEPT, ReviewAction.EDIT}
)

MIN_JUSTIFICATION_LENGTH = 20
