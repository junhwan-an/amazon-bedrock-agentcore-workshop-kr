"""CloudWatch에서 Strands Eval Session으로 매핑하는 모듈.

이 모듈은 CloudWatch OTEL span(ObservabilityClient에서 반환)을
Strands Eval의 Session 형식으로 변환하는 SessionMapper 구현을 제공합니다.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from strands_evals.mappers.session_mapper import SessionMapper
from strands_evals.types.trace import (
    AgentInvocationSpan,
    Session,
    SpanInfo,
    ToolCall,
    ToolConfig,
    ToolExecutionSpan,
    ToolResult,
    Trace,
)

from .models import Span

logger = logging.getLogger(__name__)


class CloudWatchSessionMapper(SessionMapper):
    """CloudWatch OTEL span을 Strands Eval Session 형식으로 매핑합니다.

    이 mapper는 다음을 포함한 전체 에이전트 흐름을 보존합니다:
    - 입력 및 출력이 포함된 Tool 호출
    - 사용자 프롬프트 및 응답이 포함된 Agent 호출
    - 각 trace 내 작업의 순차적 순서
    """

    def map_to_session(self, spans: list[Any], session_id: str) -> Session:
        """CloudWatch span을 Strands Eval Session으로 변환합니다.

        Args:
            spans: ObservabilityClient의 Span 객체 리스트
            session_id: Session 식별자

        Returns:
            평가 준비가 완료된 Session 객체
        """
        # trace_id별로 span 그룹화 (defaultdict로 자동 리스트 생성)
        traces_by_id = defaultdict(list)
        for span in spans:
            if isinstance(span, Span) and span.raw_message:
                # trace_id가 없으면 raw_message에서 추출, 그것도 없으면 "unknown" 사용
                trace_id = span.trace_id or span.raw_message.get("traceId", "unknown")
                traces_by_id[trace_id].append(span)

        # 각 그룹을 Trace로 변환
        traces = []
        for trace_id, trace_spans in traces_by_id.items():
            trace = self._create_trace(trace_spans, trace_id, session_id)
            if trace.spans:  # 빈 trace는 제외 (span 추출에 실패한 경우)
                traces.append(trace)

        logger.info(
            "Mapped %d CloudWatch spans to Session with %d traces",
            len(spans),
            len(traces),
        )
        return Session(traces=traces, session_id=session_id)

    def _create_trace(self, spans: list[Span], trace_id: str, session_id: str) -> Trace:
        """CloudWatch span 그룹에서 Trace를 생성합니다.

        Args:
            spans: 동일한 trace_id를 가진 Span 객체 리스트
            trace_id: trace 식별자
            session_id: session 식별자

        Returns:
            추출된 span이 포함된 Trace 객체
        """
        eval_spans = []

        # 순서를 유지하기 위해 타임스탬프로 정렬
        sorted_spans = sorted(spans, key=lambda s: s.start_time_unix_nano or 0)

        # 매칭을 위해 모든 span에서 tool 호출 및 결과 수집
        all_tool_calls = {}  # tool_use_id -> ToolCall 매핑
        all_tool_results = {}  # tool_use_id -> ToolResult 매핑

        # 첫 번째 패스: 모든 tool 호출 및 결과 수집
        for span in sorted_spans:
            raw = span.raw_message
            if not raw:
                continue

            # 출력 메시지에서 tool 호출 추출
            tool_calls = self._extract_tool_calls_from_span(raw)
            for tc in tool_calls:
                if tc.tool_call_id:
                    all_tool_calls[tc.tool_call_id] = tc

            # 입력 메시지에서 tool 결과 추출
            tool_results = self._extract_tool_results_from_span(raw)
            for tr in tool_results:
                if tr.tool_call_id:
                    all_tool_results[tr.tool_call_id] = tr

        # 호출과 결과를 매칭하여 ToolExecutionSpan 생성
        seen_tool_ids = set()  # 중복 처리 방지
        for span in sorted_spans:
            raw = span.raw_message
            if not raw:
                continue

            tool_calls = self._extract_tool_calls_from_span(raw)
            for tc in tool_calls:
                if tc.tool_call_id and tc.tool_call_id not in seen_tool_ids:
                    seen_tool_ids.add(tc.tool_call_id)
                    # 매칭되는 결과 찾기
                    tr = all_tool_results.get(tc.tool_call_id)
                    if tr is None:
                        # 결과를 찾지 못한 경우, 빈 placeholder 생성
                        tr = ToolResult(content="", tool_call_id=tc.tool_call_id)

                    span_info = self._create_span_info(span, session_id)
                    tool_exec_span = ToolExecutionSpan(
                        span_info=span_info,
                        tool_call=tc,
                        tool_result=tr,
                    )
                    eval_spans.append(tool_exec_span)

        # 최종 span에서 AgentInvocationSpan 추출 (전체 응답 포함)
        agent_span = self._extract_agent_invocation_span(sorted_spans, session_id)
        if agent_span:
            eval_spans.append(agent_span)

        return Trace(spans=eval_spans, trace_id=trace_id, session_id=session_id)

    def _extract_tool_calls_from_span(self, raw: dict) -> list[ToolCall]:
        """span의 출력 메시지에서 tool 호출을 추출합니다.

        Args:
            raw: CloudWatch span의 raw_message dict

        Returns:
            ToolCall 객체 리스트
        """
        tool_calls = []
        body = raw.get("body", {})
        output_messages = body.get("output", {}).get("messages", [])

        for msg in output_messages:
            if msg.get("role") != "assistant":
                continue

            content = msg.get("content", {})
            if not isinstance(content, dict):
                continue

            # content에서 직접 toolUse 확인
            if "toolUse" in content:
                tool_use = content["toolUse"]
                tc = ToolCall(
                    name=tool_use.get("name", ""),
                    arguments=tool_use.get("input", {}),
                    tool_call_id=tool_use.get("toolUseId"),
                )
                tool_calls.append(tc)

            # 파싱된 JSON 문자열 내부 확인 (content.content 또는 content.message)
            raw_content = content.get("content") or content.get("message")
            if isinstance(raw_content, str):
                tool_calls.extend(self._parse_tool_calls_from_json(raw_content))

        return tool_calls

    def _parse_tool_calls_from_json(self, json_str: str) -> list[ToolCall]:
        """JSON 문자열에서 tool 호출을 파싱합니다.

        Args:
            json_str: '[{"toolUse": {...}}, {"text": "..."}]'와 같은 JSON 문자열

        Returns:
            ToolCall 객체 리스트
        """
        tool_calls = []
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "toolUse" in item:
                        tool_use = item["toolUse"]
                        tc = ToolCall(
                            name=tool_use.get("name", ""),
                            arguments=tool_use.get("input", {}),
                            tool_call_id=tool_use.get("toolUseId"),
                        )
                        tool_calls.append(tc)
        except (json.JSONDecodeError, TypeError):
            pass  # JSON 파싱 실패 시 빈 리스트 반환
        return tool_calls

    def _extract_tool_results_from_span(self, raw: dict) -> list[ToolResult]:
        """span의 입력 메시지에서 tool 결과를 추출합니다.

        Args:
            raw: CloudWatch span의 raw_message dict

        Returns:
            ToolResult 객체 리스트
        """
        tool_results = []
        body = raw.get("body", {})
        input_messages = body.get("input", {}).get("messages", [])

        for msg in input_messages:
            content = msg.get("content", {})

            # content에서 직접 toolResult 처리
            if isinstance(content, dict) and "toolResult" in content:
                tr_data = content["toolResult"]
                tr = self._parse_tool_result(tr_data)
                if tr:
                    tool_results.append(tr)

            # content.content에서 JSON 문자열 처리
            if isinstance(content, dict):
                raw_content = content.get("content") or content.get("message")
                if isinstance(raw_content, str):
                    tool_results.extend(self._parse_tool_results_from_json(raw_content))

            # 직접 JSON 문자열 content 처리 (role=tool)
            if isinstance(content, str):
                tool_results.extend(self._parse_tool_results_from_json(content))

        return tool_results

    def _parse_tool_results_from_json(self, json_str: str) -> list[ToolResult]:
        """JSON 문자열에서 tool 결과를 파싱합니다.

        Args:
            json_str: '[{"toolResult": {...}}]'와 같은 JSON 문자열

        Returns:
            ToolResult 객체 리스트
        """
        tool_results = []
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and "toolResult" in item:
                        tr = self._parse_tool_result(item["toolResult"])
                        if tr:
                            tool_results.append(tr)
        except (json.JSONDecodeError, TypeError):
            pass  # JSON 파싱 실패 시 빈 리스트 반환
        return tool_results

    def _parse_tool_result(self, tr_data: dict) -> ToolResult | None:
        """단일 tool 결과 dict를 ToolResult 객체로 파싱합니다.

        Args:
            tr_data: toolResult 데이터가 포함된 Dict

        Returns:
            ToolResult 객체 또는 None
        """
        if not isinstance(tr_data, dict):
            return None

        # content 추출 - 문자열 또는 content 블록 리스트일 수 있음
        content_raw = tr_data.get("content", "")
        if isinstance(content_raw, list):
            # content 블록 리스트에서 text 필드만 추출하여 결합
            texts = []
            for block in content_raw:
                if isinstance(block, dict) and "text" in block:
                    texts.append(block["text"])
            content = "\n".join(texts)
        else:
            content = str(content_raw)

        return ToolResult(
            content=content,
            error=tr_data.get("error"),
            tool_call_id=tr_data.get("toolUseId"),
        )

    def _extract_agent_invocation_span(
        self, spans: list[Span], session_id: str
    ) -> AgentInvocationSpan | None:
        """span 리스트에서 AgentInvocationSpan을 추출합니다.

        첫 번째 span에서 사용자 프롬프트를 찾고,
        가장 긴 출력을 가진 span에서 최종 응답을 찾습니다.

        Args:
            spans: 정렬된 Span 객체 리스트
            session_id: Session 식별자

        Returns:
            AgentInvocationSpan 또는 추출 실패 시 None
        """
        if not spans:
            return None

        # 첫 번째 메시지에서 사용자 프롬프트 가져오기
        user_prompt = None
        for span in spans:
            raw = span.raw_message
            if not raw:
                continue
            prompt = self._extract_user_prompt(raw)
            if prompt:
                user_prompt = prompt
                break

        if not user_prompt:
            return None

        # 가장 긴 출력을 가진 span에서 agent 응답 가져오기 (최종 답변)
        best_response = ""
        best_span = None
        for span in spans:
            raw = span.raw_message
            if not raw:
                continue
            response = self._extract_agent_response(raw)
            if response and len(response) > len(best_response):
                best_response = response
                best_span = span

        if not best_response or not best_span:
            return None

        # 사용 가능한 tool 추출 (system 메시지가 있는 경우)
        available_tools = self._extract_available_tools(spans)

        span_info = self._create_span_info(best_span, session_id)
        return AgentInvocationSpan(
            span_info=span_info,
            user_prompt=user_prompt,
            agent_response=best_response,
            available_tools=available_tools,
        )

    def _extract_user_prompt(self, raw: dict) -> str | None:
        """span에서 사용자 프롬프트 텍스트를 추출합니다.

        Args:
            raw: raw_message dict

        Returns:
            사용자 프롬프트 문자열 또는 None
        """
        body = raw.get("body", {})
        input_messages = body.get("input", {}).get("messages", [])

        for msg in input_messages:
            if msg.get("role") != "user":
                continue

            content = msg.get("content", {})
            text = self._extract_text_from_content(content)
            if text:
                return text

        return None

    def _extract_agent_response(self, raw: dict) -> str | None:
        """span에서 agent 응답 텍스트를 추출합니다.

        Args:
            raw: raw_message dict

        Returns:
            Agent 응답 문자열 또는 None
        """
        body = raw.get("body", {})
        output_messages = body.get("output", {}).get("messages", [])

        # 실제 텍스트가 있는 마지막 assistant 메시지 가져오기 (tool 호출만 있는 것 제외)
        best_response = ""
        for msg in output_messages:
            if msg.get("role") != "assistant":
                continue

            content = msg.get("content", {})

            # 직접 message 필드 확인 (최종 응답)
            if isinstance(content, dict):
                direct_msg = content.get("message")
                if isinstance(direct_msg, str) and not direct_msg.startswith("[{"):
                    # JSON 배열 문자열이 아닌 실제 응답 텍스트
                    if len(direct_msg) > len(best_response):
                        best_response = direct_msg
                    continue

            text = self._extract_text_from_content(content)
            if text and len(text) > len(best_response):
                best_response = text

        return best_response if best_response else None

    def _extract_text_from_content(self, content: Any) -> str | None:
        """content 필드에서 텍스트를 추출합니다.

        Args:
            content: Content dict 또는 문자열

        Returns:
            추출된 텍스트 또는 None
        """
        if isinstance(content, str):
            return content

        if not isinstance(content, dict):
            return None

        # content.content 또는 content.message 시도
        raw_content = content.get("content") or content.get("message")

        if isinstance(raw_content, str):
            # JSON 배열로 파싱 시도
            try:
                parsed = json.loads(raw_content)
                if isinstance(parsed, list):
                    texts = []
                    for item in parsed:
                        if isinstance(item, dict) and "text" in item:
                            texts.append(item["text"])
                    if texts:
                        return " ".join(texts)
            except (json.JSONDecodeError, TypeError):
                # JSON이 아닌 일반 문자열, 그대로 반환
                return raw_content

        return None

    def _extract_available_tools(self, spans: list[Span]) -> list[ToolConfig]:
        """system 메시지 또는 span 속성에서 사용 가능한 tool을 추출합니다.

        Args:
            spans: Span 객체 리스트

        Returns:
            ToolConfig 객체 리스트
        """
        # 실제 tool 호출에서 tool 이름을 추출 (간단한 구현)
        # 더 완전한 구현은 system 메시지에서 tool 정의를 파싱할 것
        tool_names = set()
        for span in spans:
            raw = span.raw_message
            if not raw:
                continue
            tool_calls = self._extract_tool_calls_from_span(raw)
            for tc in tool_calls:
                tool_names.add(tc.name)

        return [ToolConfig(name=name) for name in sorted(tool_names)]

    def _create_span_info(self, span: Span, session_id: str) -> SpanInfo:
        """CloudWatch Span에서 SpanInfo를 생성합니다.

        Args:
            span: Span 객체
            session_id: Session 식별자

        Returns:
            SpanInfo 객체
        """
        raw = span.raw_message or {}

        # 나노초 타임스탬프를 datetime 객체로 변환
        start_nano = span.start_time_unix_nano or raw.get("startTimeUnixNano", 0)
        end_nano = raw.get("endTimeUnixNano", start_nano)

        # 1e9로 나누어 초 단위로 변환 후 datetime 생성
        start_time = datetime.fromtimestamp(start_nano / 1e9, tz=timezone.utc)
        end_time = datetime.fromtimestamp(end_nano / 1e9, tz=timezone.utc)

        return SpanInfo(
            trace_id=span.trace_id,
            span_id=span.span_id,
            session_id=session_id,
            parent_span_id=raw.get("parentSpanId"),
            start_time=start_time,
            end_time=end_time,
        )
