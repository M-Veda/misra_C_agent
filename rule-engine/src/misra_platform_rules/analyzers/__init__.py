"""Shared, reusable analysis infrastructure for MISRA rule plugins.

Rules MUST reuse these services instead of duplicating essential-type,
cast, pointer, qualifier, control-flow, dataflow, symbol, linkage, macro, or
expression-classification logic inline. This keeps ~150 rule implementations
consistent and makes semantic fixes (e.g. a better narrowing check) apply to
every rule that uses that analyzer at once.
"""

from misra_platform_rules.analyzers.alias_analyzer import AliasAnalyzer
from misra_platform_rules.analyzers.cast_analyzer import CastAnalyzer
from misra_platform_rules.analyzers.cfg_builder import CFGBuilder
from misra_platform_rules.analyzers.cfg_engine import CFGEngine, ControlFlowGraph
from misra_platform_rules.analyzers.dataflow_engine import DataFlowEngine
from misra_platform_rules.analyzers.dataflow_engine_v2 import DataFlowEngineV2
from misra_platform_rules.analyzers.essential_type_analyzer import EssentialTypeAnalyzer
from misra_platform_rules.analyzers.essential_type_engine import EssentialTypeEngine
from misra_platform_rules.analyzers.expression_classifier import ExpressionClassifier
from misra_platform_rules.analyzers.linkage_analyzer import LinkageAnalyzer
from misra_platform_rules.analyzers.linkage_index import LinkageIndex
from misra_platform_rules.analyzers.macro_analyzer import MacroAnalyzer
from misra_platform_rules.analyzers.pointer_analyzer import PointerAnalyzer
from misra_platform_rules.analyzers.qualifier_analyzer import QualifierAnalyzer
from misra_platform_rules.analyzers.symbol_index import SymbolIndex

__all__ = [
    "AliasAnalyzer",
    "CastAnalyzer",
    "CFGBuilder",
    "CFGEngine",
    "ControlFlowGraph",
    "DataFlowEngine",
    "DataFlowEngineV2",
    "EssentialTypeAnalyzer",
    "EssentialTypeEngine",
    "ExpressionClassifier",
    "LinkageAnalyzer",
    "LinkageIndex",
    "MacroAnalyzer",
    "PointerAnalyzer",
    "QualifierAnalyzer",
    "SymbolIndex",
]
