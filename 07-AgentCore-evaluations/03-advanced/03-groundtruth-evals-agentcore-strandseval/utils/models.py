"""trace 데이터 및 evaluation을 위한 데이터 모델."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from strands_evals.mappers.session_mapper import SessionMapper
    from strands_evals.types.trace import Session


@dataclass
class Span:
    """trace 메타데이터를 포함한 OpenTelemetry span."""

    trace_id: str
    span_id: str
    span_name: str
    start_time_unix_nano: Optional[int] = None
    raw_message: Optional[Dict[str, Any]] = None

    @classmethod
    def from_cloudwatch_result(cls, result: Any) -> "Span":
        """CloudWatch Logs Insights 쿼리 결과로부터 Span을 생성합니다."""
        # CloudWatch 결과는 list 또는 dict 형태로 올 수 있음
        fields = result if isinstance(result, list) else result.get("fields", [])

        def get_field(field_name: str, default: Any = None) -> Any:
            # fields 배열에서 field 이름으로 value 추출
            for field_item in fields:
                if field_item.get("field") == field_name:
                    return field_item.get("value", default)
            return default

        def parse_json_field(field_name: str) -> Any:
            value = get_field(field_name)
            if value and isinstance(value, str):
                try:
                    return json.loads(value)
                except Exception:
                    return value
            return value

        def get_int_field(field_name: str) -> Optional[int]:
            value = get_field(field_name)
            if value is not None:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None
            return None

        return cls(
            trace_id=get_field("traceId", ""),
            span_id=get_field("spanId", ""),
            span_name=get_field("spanName", ""),
            start_time_unix_nano=get_int_field("startTimeUnixNano"),
            raw_message=parse_json_field("@message"),
        )


@dataclass
class RuntimeLog:
    """agent 전용 로그 그룹의 런타임 로그 항목."""

    timestamp: str
    message: str
    span_id: Optional[str] = None
    trace_id: Optional[str] = None
    raw_message: Optional[Dict[str, Any]] = None

    @classmethod
    def from_cloudwatch_result(cls, result: Any) -> "RuntimeLog":
        """CloudWatch Logs Insights 쿼리 결과로부터 RuntimeLog를 생성합니다."""
        # CloudWatch 결과는 list 또는 dict 형태로 올 수 있음
        fields = result if isinstance(result, list) else result.get("fields", [])

        def get_field(field_name: str, default: Any = None) -> Any:
            # fields 배열에서 field 이름으로 value 추출
            for field_item in fields:
                if field_item.get("field") == field_name:
                    return field_item.get("value", default)
            return default

        def parse_json_field(field_name: str) -> Any:
            value = get_field(field_name)
            if value and isinstance(value, str):
                try:
                    return json.loads(value)
                except Exception:
                    return value
            return value

        return cls(
            timestamp=get_field("@timestamp", ""),
            message=get_field("@message", ""),
            span_id=get_field("spanId"),
            trace_id=get_field("traceId"),
            raw_message=parse_json_field("@message"),
        )


@dataclass
class TraceData:
    """span과 런타임 로그를 포함한 완전한 세션 데이터."""

    session_id: Optional[str] = None
    spans: List[Span] = field(default_factory=list)
    runtime_logs: List[RuntimeLog] = field(default_factory=list)

    def get_trace_ids(self) -> List[str]:
        """span으로부터 모든 고유한 trace ID를 가져옵니다."""
        return list(set(span.trace_id for span in self.spans if span.trace_id))

    def get_tool_execution_spans(self, tool_name_filter: Optional[str] = None) -> List[str]:
        """tool 실행 span의 span ID를 가져옵니다.

        Args:
            tool_name_filter: 필터링할 tool 이름 (예: "calculate_bmi")

        Returns:
            gen_ai.operation.name == "execute_tool"인 span ID 목록
        """
        tool_span_ids = []

        for span in self.spans:
            if not span.raw_message:
                continue

            attributes = span.raw_message.get("attributes", {})

            # OpenTelemetry gen_ai semantic convention에서 tool 실행 여부 확인
            operation_name = attributes.get("gen_ai.operation.name")
            if operation_name != "execute_tool":
                continue

            # tool 이름 필터가 제공된 경우 적용
            if tool_name_filter:
                tool_name = attributes.get("gen_ai.tool.name")
                if tool_name != tool_name_filter:
                    continue

            tool_span_ids.append(span.span_id)

        return tool_span_ids

    def to_session(self, mapper: SessionMapper) -> Session:
        """제공된 mapper를 사용하여 Strands Eval Session으로 변환합니다.

        Args:
            mapper: SessionMapper 구현체 (예: CloudWatchSessionMapper)

        Returns:
            evaluation 준비가 완료된 Session 객체
        """
        # Strands Eval 라이브러리의 Session 형식으로 변환
        return mapper.map_to_session(self.spans, self.session_id or "")


class EvaluationRequest:
    """evaluation API를 위한 요청 페이로드."""

    def __init__(
        self,
        evaluator_id: str,
        session_spans: List[Dict[str, Any]],
        evaluation_target: Optional[Dict[str, Any]] = None
    ):
        self.evaluator_id = evaluator_id
        self.session_spans = session_spans
        self.evaluation_target = evaluation_target

    def to_api_request(self) -> tuple:
        """API 요청 형식으로 변환합니다.

        Returns:
            (evaluator_id_param, request_body) 튜플
        """
        # Bedrock Agent evaluation API 요청 형식으로 변환
        request_body = {"evaluationInput": {"sessionSpans": self.session_spans}}

        if self.evaluation_target:
            request_body["evaluationTarget"] = self.evaluation_target

        return self.evaluator_id, request_body


@dataclass
class EvaluationResult:
    """evaluation API의 결과."""

    evaluator_id: str
    evaluator_name: str
    evaluator_arn: str
    explanation: str
    context: Dict[str, Any]
    value: Optional[float] = None
    label: Optional[str] = None
    token_usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None

    @classmethod
    def from_api_response(cls, api_result: Dict[str, Any]) -> "EvaluationResult":
        """API 응답으로부터 EvaluationResult를 생성합니다."""
        return cls(
            evaluator_id=api_result.get("evaluatorId", ""),
            evaluator_name=api_result.get("evaluatorName", ""),
            evaluator_arn=api_result.get("evaluatorArn", ""),
            explanation=api_result.get("explanation", ""),
            context=api_result.get("context", {}),
            value=api_result.get("value"),  # numeric score (없으면 None)
            label=api_result.get("label"),  # categorical label (없으면 None)
            token_usage=api_result.get("tokenUsage"),  # 없으면 None
            error=None,
        )


@dataclass
class EvaluationResults:
    """세션에 대한 evaluation 결과 모음."""

    session_id: str
    results: List[EvaluationResult] = field(default_factory=list)
    input_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def add_result(self, result: EvaluationResult) -> None:
        """evaluation 결과를 추가합니다."""
        self.results.append(result)

    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화를 위해 딕셔너리로 변환합니다."""
        output = {
            "session_id": self.session_id,
            "results": [
                {
                    "evaluator_id": r.evaluator_id,
                    "evaluator_name": r.evaluator_name,
                    "evaluator_arn": r.evaluator_arn,
                    "value": r.value,
                    "label": r.label,
                    "explanation": r.explanation,
                    "context": r.context,
                    "token_usage": r.token_usage,
                    "error": r.error,
                }
                for r in self.results
            ],
        }
        if self.metadata:
            output["metadata"] = self.metadata
        if self.input_data:
            output["input_data"] = self.input_data
        return output


@dataclass
class SessionInfo:
    """발견된 세션에 대한 정보.

    Attributes:
        session_id: 세션의 고유 식별자
        span_count: span 수 (time_based) 또는 evaluation 수 (score_based)
            - time_based discovery의 경우: trace의 실제 span 수
            - score_based discovery의 경우: evaluation 수 (metadata.eval_count에도 있음)
        first_seen: 첫 번째 활동의 타임스탬프
        last_seen: 마지막 활동의 타임스탬프
        trace_count: 고유한 trace 수 (time_based discovery에만 해당)
        discovery_method: 세션이 발견된 방법 ("time_based" 또는 "score_based")
        metadata: 추가 데이터 (score_based의 경우: avg_score, min_score, max_score, eval_count)
    """

    session_id: str
    span_count: int
    first_seen: datetime
    last_seen: datetime
    trace_count: Optional[int] = None
    discovery_method: Optional[str] = None  # "time_based" 또는 "score_based"
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화를 위해 딕셔너리로 변환합니다."""
        return {
            "session_id": self.session_id,
            "span_count": self.span_count,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "trace_count": self.trace_count,
            "discovery_method": self.discovery_method,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionInfo":
        """딕셔너리로부터 SessionInfo를 생성합니다."""
        first_seen = data["first_seen"]
        last_seen = data["last_seen"]

        # ISO 형식 문자열을 datetime으로 파싱하고 timezone-aware로 변환
        if isinstance(first_seen, str):
            first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
        if first_seen.tzinfo is None:
            first_seen = first_seen.replace(tzinfo=timezone.utc)

        if isinstance(last_seen, str):
            last_seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)

        return cls(
            session_id=data["session_id"],
            span_count=data["span_count"],
            first_seen=first_seen,
            last_seen=last_seen,
            trace_count=data.get("trace_count"),
            discovery_method=data.get("discovery_method"),
            metadata=data.get("metadata"),
        )


@dataclass
class SessionDiscoveryResult:
    """세션 발견 작업의 결과."""

    sessions: List[SessionInfo]
    discovery_time: datetime
    log_group: str
    time_range_start: datetime
    time_range_end: datetime
    discovery_method: str
    filter_criteria: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """JSON 직렬화를 위해 딕셔너리로 변환합니다."""
        return {
            "sessions": [s.to_dict() for s in self.sessions],
            "discovery_time": self.discovery_time.isoformat(),
            "log_group": self.log_group,
            "time_range_start": self.time_range_start.isoformat(),
            "time_range_end": self.time_range_end.isoformat(),
            "discovery_method": self.discovery_method,
            "filter_criteria": self.filter_criteria,
        }

    def save_to_json(self, filepath: str) -> None:
        """발견 결과를 JSON 파일로 저장합니다."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_json(cls, filepath: str) -> "SessionDiscoveryResult":
        """JSON 파일로부터 발견 결과를 로드합니다."""
        with open(filepath, "r") as f:
            data = json.load(f)

        return cls(
            sessions=[SessionInfo.from_dict(s) for s in data["sessions"]],
            discovery_time=datetime.fromisoformat(
                data["discovery_time"].replace("Z", "+00:00")
            ),
            log_group=data["log_group"],
            time_range_start=datetime.fromisoformat(
                data["time_range_start"].replace("Z", "+00:00")
            ),
            time_range_end=datetime.fromisoformat(
                data["time_range_end"].replace("Z", "+00:00")
            ),
            discovery_method=data["discovery_method"],
            filter_criteria=data.get("filter_criteria"),
        )

    def get_session_ids(self) -> List[str]:
        """세션 ID 목록을 가져옵니다."""
        return [s.session_id for s in self.sessions]
