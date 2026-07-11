"""Import models for Alembic autogenerate."""

from misra_platform.domain.models.analysis import (  # noqa: F401
    AnalysisRun,
    FileIndexEntry,
    IncrementalManifest,
    Project,
    TranslationUnitRecord,
)
from misra_platform.domain.models.review import (  # noqa: F401
    AuditEntryRecord,
    PatchRecord,
    ViolationReviewRecord,
)
from misra_platform.domain.models.enterprise import (  # noqa: F401
    ComplianceSnapshotRecord,
    IntegrationConfigRecord,
    TeamMemberRecord,
    TeamRecord,
)
from misra_platform.domain.models.violations import (  # noqa: F401
    RuleExecutionMetricRecord,
    RuleRunStatisticsRecord,
    ViolationRecord,
)
