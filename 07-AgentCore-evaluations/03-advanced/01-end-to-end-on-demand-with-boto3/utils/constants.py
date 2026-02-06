"""CloudWatch trace 데이터 내보내기 및 평가를 위한 상수."""

import os

# 환경변수에서 설정값 로드 (기본값 제공)
DEFAULT_MAX_EVALUATION_ITEMS = int(os.getenv("AGENTCORE_MAX_EVAL_ITEMS", "1000"))
MAX_SPAN_IDS_IN_CONTEXT = int(os.getenv("AGENTCORE_MAX_SPAN_IDS", "20"))

DEFAULT_RUNTIME_SUFFIX = "DEFAULT"

EVALUATION_OUTPUT_DIR = "evaluation_output"
EVALUATION_INPUT_DIR = "evaluation_input"
DASHBOARD_DATA_FILE = "dashboard_data.js"
DASHBOARD_HTML_FILE = "evaluation_dashboard.html"
EVALUATION_OUTPUT_PATTERN = "*.json"
DEFAULT_FILE_ENCODING = "utf-8"

# sessionId 기반 평가 - 세션 전체 trace 데이터 필요
SESSION_SCOPED_EVALUATORS = {
    "Builtin.GoalSuccessRate",
}

# spanId 기반 평가 - 개별 span(tool 호출) 데이터 필요
SPAN_SCOPED_EVALUATORS = {
    "Builtin.ToolSelectionAccuracy",
    "Builtin.ToolParameterAccuracy",
}

# spanId 불필요 - session 또는 trace 레벨에서 평가 가능
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
    """OpenTelemetry 속성 접두사."""
    GEN_AI = "gen_ai"