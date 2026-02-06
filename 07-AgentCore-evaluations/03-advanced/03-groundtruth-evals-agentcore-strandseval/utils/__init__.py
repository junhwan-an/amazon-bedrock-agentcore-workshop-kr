"""Utilities for CloudWatch to Strands Eval conversion with multi-session support.

This module provides utilities for:
- Querying CloudWatch Logs for OTEL traces (ObservabilityClient)
- Discovering sessions from CloudWatch log groups (time-based and score-based)
- Mapping CloudWatch spans to Strands Eval Session format (CloudWatchSessionMapper)
- Data models for spans, sessions, and evaluation results
- Custom CloudWatch logging with original trace IDs (send_evaluation_to_cloudwatch)

Note: Configuration is in config.py (same directory as notebooks).
"""

from .cloudwatch_client import CloudWatchQueryBuilder, ObservabilityClient
from .evaluation_cloudwatch_logger import (
    EvaluationLogConfig,
    log_evaluation_batch,
    send_evaluation_to_cloudwatch,
)
from .models import (
    EvaluationRequest,
    EvaluationResult,
    EvaluationResults,
    RuntimeLog,
    SessionDiscoveryResult,
    SessionInfo,
    Span,
    TraceData,
)
from .session_mapper import CloudWatchSessionMapper

__all__ = [
    # CloudWatch 클라이언트
    "ObservabilityClient",
    "CloudWatchQueryBuilder",
    # Session 매퍼
    "CloudWatchSessionMapper",
    # 커스텀 CloudWatch 로거
    "send_evaluation_to_cloudwatch",
    "log_evaluation_batch",
    "EvaluationLogConfig",
    # Model들
    "Span",
    "RuntimeLog",
    "TraceData",
    "SessionInfo",
    "SessionDiscoveryResult",
    "EvaluationRequest",
    "EvaluationResult",
    "EvaluationResults",
]
