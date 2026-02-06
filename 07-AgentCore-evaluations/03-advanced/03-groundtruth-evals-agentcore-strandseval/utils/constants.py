"""CloudWatch trace 데이터 내보내기 및 평가를 위한 상수."""

import os

# API 설정
# 환경변수로 평가 항목 최대 개수 설정 가능 (기본값: 1000)
DEFAULT_MAX_EVALUATION_ITEMS = int(os.getenv("AGENTCORE_MAX_EVAL_ITEMS", "1000"))
# context에 포함할 span ID 최대 개수 (기본값: 20)
MAX_SPAN_IDS_IN_CONTEXT = int(os.getenv("AGENTCORE_MAX_SPAN_IDS", "20"))

DEFAULT_RUNTIME_SUFFIX = "DEFAULT"

# Dashboard 설정
EVALUATION_OUTPUT_DIR = "evaluation_output"
EVALUATION_INPUT_DIR = "evaluation_input"
DASHBOARD_DATA_FILE = "dashboard_data.js"
DASHBOARD_HTML_FILE = "evaluation_dashboard.html"
EVALUATION_OUTPUT_PATTERN = "*.json"
DEFAULT_FILE_ENCODING = "utf-8"

# Session 범위 Evaluator: sessionId만 필요, 세션 전체 trace 데이터 분석
SESSION_SCOPED_EVALUATORS = {
    "Builtin.GoalSuccessRate",
}

# Span 범위 Evaluator: spanIds 필요, 특정 span(tool 호출) 데이터 분석
SPAN_SCOPED_EVALUATORS = {
    "Builtin.ToolSelectionAccuracy",
    "Builtin.ToolParameterAccuracy",
}

# 유연한 범위 Evaluator: span ID 불필요, session/trace 레벨에서 작동
FLEXIBLE_SCOPED_EVALUATORS = {
    "Builtin.Correctness",
    "Builtin.Faithfulness",
    "Builtin.Helpfulness",
    "Builtin.ResponseRelevance",
    "Builtin.Conciseness",
    "Builtin.Coherence",
    "Builtin.InstructionFollowing",
    "Builtin.Refusal",
    "Builtin.Harmfulness",
    "Builtin.Stereotyping",
}


class AttributePrefixes:
    """OpenTelemetry attribute 접두사."""
    GEN_AI = "gen_ai"