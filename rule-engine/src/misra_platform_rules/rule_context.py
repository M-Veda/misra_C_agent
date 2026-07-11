from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from misra_platform_rules.analysis_cache import AnalysisCache


@dataclass(slots=True)
class ProjectConfiguration:
    enabled_rules: list[str] = field(default_factory=list)
    severity_overrides: dict[str, str] = field(default_factory=dict)
    standard_version: str = "misra_c_2012"


@dataclass(slots=True)
class PreviousViolation:
    fingerprint: str
    rule_id: str
    file_path: str
    status: str


@dataclass(slots=True)
class RuleContext:
    translation_unit_id: str
    file_path: str
    ast_nodes: list[dict[str, Any]]
    source_manager: dict[str, Any]
    type_system: dict[str, dict[str, Any]]
    typedef_chains: dict[str, str]
    macro_table: dict[str, Any]
    include_graph: dict[str, list[str]]
    project_config: ProjectConfiguration
    previous_violations: list[PreviousViolation]
    toolchain_profile: dict[str, Any]
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    preprocessor: dict[str, Any] = field(default_factory=dict)
    cross_tu_linkage: dict[str, Any] = field(default_factory=dict)
    analysis_cache: "AnalysisCache | None" = None

    def __post_init__(self) -> None:
        if self.analysis_cache is None:
            # Local import to avoid a rule_context <-> analysis_cache <->
            # analyzers import cycle at module load time.
            from misra_platform_rules.analysis_cache import AnalysisCache

            self.analysis_cache = AnalysisCache()

    @classmethod
    def from_ast_artifact(
        cls,
        *,
        artifact: dict[str, Any],
        translation_unit_id: str,
        include_graph: dict[str, list[str]] | None = None,
        project_config: ProjectConfiguration | None = None,
        previous_violations: list[PreviousViolation] | None = None,
        toolchain_profile: dict[str, Any] | None = None,
        cross_tu_linkage: dict[str, Any] | None = None,
    ) -> "RuleContext":
        nodes = artifact.get("nodes", [])
        type_system = {
            node["node_id"]: node.get("type_information", {}) for node in nodes if "node_id" in node
        }
        typedef_chains = {
            node["node_id"]: node.get("type_information", {}).get("typedef_chain", "")
            for node in nodes
            if node.get("type_information", {}).get("typedef_chain")
        }
        macro_table = artifact.get("preprocessor", {})
        file_path = artifact.get("file_path", "")

        return cls(
            translation_unit_id=translation_unit_id,
            file_path=file_path,
            ast_nodes=nodes,
            source_manager={"primary_file": file_path},
            type_system=type_system,
            typedef_chains=typedef_chains,
            macro_table=macro_table,
            include_graph=include_graph or {},
            project_config=project_config or ProjectConfiguration(),
            previous_violations=previous_violations or [],
            toolchain_profile=toolchain_profile or {},
            diagnostics=artifact.get("diagnostics", []),
            preprocessor=artifact.get("preprocessor", {}),
            cross_tu_linkage=cross_tu_linkage or {},
        )
