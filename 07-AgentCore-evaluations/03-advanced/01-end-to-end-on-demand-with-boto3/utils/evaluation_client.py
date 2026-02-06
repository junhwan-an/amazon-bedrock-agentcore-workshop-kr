"""AgentCore Evaluation DataPlane API를 위한 클라이언트."""

import json
import os
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from .cloudwatch_client import ObservabilityClient
from .constants import (
    DASHBOARD_DATA_FILE,
    DASHBOARD_HTML_FILE,
    DEFAULT_FILE_ENCODING,
    DEFAULT_MAX_EVALUATION_ITEMS,
    DEFAULT_RUNTIME_SUFFIX,
    EVALUATION_OUTPUT_DIR,
    EVALUATION_OUTPUT_PATTERN,
    SESSION_SCOPED_EVALUATORS,
    SPAN_SCOPED_EVALUATORS,
)
from .models import EvaluationRequest, EvaluationResult, EvaluationResults, TraceData


class EvaluationClient:
    """AgentCore Evaluation Data Plane API를 위한 클라이언트."""

    DEFAULT_REGION = "us-east-1"

    def __init__(
        self, region: Optional[str] = None, boto_client: Optional[Any] = None
    ):
        """evaluation 클라이언트를 초기화합니다.

        Args:
            region: AWS 리전 (기본값은 환경 변수 또는 us-east-1)
            boto_client: 테스트를 위한 선택적 사전 구성된 boto3 클라이언트
        """
        self.region = region or os.getenv("AGENTCORE_EVAL_REGION", self.DEFAULT_REGION)
        
        if boto_client:
            self.client = boto_client
        else:
            self.client = boto3.client(
                "agentcore-evaluation-dataplane", region_name=self.region
            )

    def _validate_scope_compatibility(self, evaluator_id: str, scope: str) -> None:
        """evaluator가 요청된 scope와 호환되는지 검증합니다.

        Args:
            evaluator_id: evaluator 식별자
            scope: evaluation scope ("session", "trace", 또는 "span")

        Raises:
            ValueError: evaluator-scope 조합이 유효하지 않은 경우
        """
        # span scope는 특정 evaluator만 지원
        if scope == "span":
            if evaluator_id not in SPAN_SCOPED_EVALUATORS:
                raise ValueError(
                    f"{evaluator_id} cannot use span scope. "
                    f"Only {SPAN_SCOPED_EVALUATORS} support span-level evaluation."
                )

        elif scope == "trace":
            # trace scope는 session/span 전용 evaluator와 호환 불가
            if evaluator_id in SESSION_SCOPED_EVALUATORS:
                raise ValueError(f"{evaluator_id} requires session scope (cannot use trace scope)")
            if evaluator_id in SPAN_SCOPED_EVALUATORS:
                raise ValueError(f"{evaluator_id} requires span scope (cannot use trace scope)")

        elif scope == "session":
            if evaluator_id in SPAN_SCOPED_EVALUATORS:
                raise ValueError(f"{evaluator_id} requires span scope (cannot use session scope)")

        else:
            raise ValueError(f"Invalid scope: {scope}. Must be 'session', 'trace', or 'span'")

    def _build_evaluation_target(
        self, scope: str, trace_id: Optional[str] = None, span_ids: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """scope에 따라 evaluationTarget을 구성합니다.

        Args:
            scope: evaluation scope ("session", "trace", 또는 "span")
            trace_id: trace scope를 위한 Trace ID
            span_ids: span scope를 위한 Span ID 목록

        Returns:
            evaluationTarget dict 또는 session scope의 경우 None

        Raises:
            ValueError: scope에 필요한 ID가 누락된 경우
        """
        if scope == "session":
            return None

        elif scope == "trace":
            if not trace_id:
                raise ValueError("trace_id is required when scope='trace'")
            return {"traceIds": [trace_id]}

        elif scope == "span":
            if not span_ids:
                raise ValueError("span_ids are required when scope='span'")
            return {"spanIds": span_ids}

        else:
            raise ValueError(f"Invalid scope: {scope}. Must be 'session', 'trace', or 'span'")

    def _extract_raw_spans(self, trace_data: TraceData) -> List[Dict[str, Any]]:
        """TraceData에서 원시 span 문서를 추출합니다.

        Args:
            trace_data: span과 runtime 로그를 포함하는 TraceData

        Returns:
            원시 span 문서 목록
        """
        raw_spans = []

        for span in trace_data.spans:
            if span.raw_message:
                raw_spans.append(span.raw_message)

        for log in trace_data.runtime_logs:
            if log.raw_message:
                raw_spans.append(log.raw_message)

        return raw_spans

    def _filter_relevant_spans(self, raw_spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """evaluation을 위한 높은 신호 span만 필터링합니다.

        다음만 유지합니다:
        - gen_ai.* 속성을 가진 Span (LLM 호출, agent 작업)
        - 대화 데이터를 가진 로그 이벤트 (입력/출력 메시지)

        Args:
            raw_spans: 원시 span/로그 문서 목록

        Returns:
            관련 span의 필터링된 목록
        """
        relevant_spans = []
        for span_doc in raw_spans:
            # gen_ai로 시작하는 속성이 있으면 LLM 관련 span으로 판단
            attributes = span_doc.get("attributes", {})
            if any(k.startswith("gen_ai") for k in attributes.keys()):
                relevant_spans.append(span_doc)
                continue

            # body에 input/output이 있으면 대화 데이터로 판단
            body = span_doc.get("body", {})
            if isinstance(body, dict) and ("input" in body or "output" in body):
                relevant_spans.append(span_doc)

        return relevant_spans

    def _get_most_recent_session_spans(
        self, trace_data: TraceData, max_items: int = DEFAULT_MAX_EVALUATION_ITEMS
    ) -> List[Dict[str, Any]]:
        """세션의 모든 trace에서 가장 최근의 관련 span을 가져옵니다.

        Args:
            trace_data: 모든 세션 데이터를 포함하는 TraceData
            max_items: 반환할 최대 항목 수

        Returns:
            원시 span 문서 목록, 가장 최근 순
        """
        raw_spans = self._extract_raw_spans(trace_data)

        if not raw_spans:
            return []

        relevant_spans = self._filter_relevant_spans(raw_spans)

        # 타임스탬프 기준으로 정렬 (최신순)
        def get_timestamp(span_doc):
            return span_doc.get("startTimeUnixNano") or span_doc.get("timeUnixNano") or 0

        relevant_spans.sort(key=get_timestamp, reverse=True)

        return relevant_spans[:max_items]

    def _fetch_session_data(self, session_id: str, agent_id: str, region: str) -> TraceData:
        """CloudWatch에서 세션 데이터를 가져옵니다.

        Args:
            session_id: 가져올 Session ID
            agent_id: 필터링을 위한 Agent ID
            region: AWS 리전

        Returns:
            세션 span과 로그를 포함하는 TraceData

        Raises:
            RuntimeError: 세션 데이터를 가져올 수 없는 경우
        """
        obs_client = ObservabilityClient(region_name=region, agent_id=agent_id, runtime_suffix=DEFAULT_RUNTIME_SUFFIX)

        # 최근 7일간의 데이터 조회
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)

        try:
            trace_data = obs_client.get_session_data(
                session_id=session_id, start_time_ms=start_time_ms, end_time_ms=end_time_ms, include_runtime_logs=True
            )
        except Exception as e:
            raise RuntimeError(f"Failed to fetch session data: {e}") from e

        if not trace_data or not trace_data.spans:
            raise RuntimeError(f"No trace data found for session {session_id}")

        return trace_data

    def _count_span_types(self, raw_spans: List[Dict[str, Any]]) -> tuple:
        """span, 로그, gen_ai span을 카운트합니다.

        Args:
            raw_spans: 원시 span 문서 목록

        Returns:
            (spans_count, logs_count, genai_spans_count) 튜플
        """
        spans_count = sum(1 for item in raw_spans if "spanId" in item and "startTimeUnixNano" in item)
        logs_count = sum(1 for item in raw_spans if "body" in item and "timeUnixNano" in item)
        genai_spans = sum(
            1
            for span in raw_spans
            if "spanId" in span and any(k.startswith("gen_ai") for k in span.get("attributes", {}).keys())
        )
        return spans_count, logs_count, genai_spans

    def _save_input(
        self,
        session_id: str,
        otel_spans: List[Dict[str, Any]],
    ) -> str:
        """입력 데이터를 JSON 파일로 저장합니다.

        evaluate API로 전송되는 span만 저장합니다.

        Args:
            session_id: Session ID
            otel_spans: API로 전송되는 Span

        Returns:
            저장된 파일 경로
        """
        from .constants import EVALUATION_INPUT_DIR
        os.makedirs(EVALUATION_INPUT_DIR, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_short = session_id[:16] if len(session_id) > 16 else session_id
        filename = f"{EVALUATION_INPUT_DIR}/input_{session_short}_{timestamp}.json"

        # API 입력으로 전송되는 span만 저장
        with open(filename, "w", encoding=DEFAULT_FILE_ENCODING) as f:
            json.dump(otel_spans, f, indent=2)

        print(f"Input saved to: {filename}")
        return filename

    def _save_output(self, results: EvaluationResults) -> str:
        """evaluation 결과를 JSON 파일로 저장합니다.

        Args:
            results: EvaluationResults 객체

        Returns:
            저장된 파일 경로
        """
        os.makedirs(EVALUATION_OUTPUT_DIR, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_short = results.session_id[:16] if len(results.session_id) > 16 else results.session_id
        filename = f"{EVALUATION_OUTPUT_DIR}/output_{session_short}_{timestamp}.json"

        with open(filename, "w", encoding=DEFAULT_FILE_ENCODING) as f:
            json.dump(results.to_dict(), f, indent=2)

        print(f"Output saved to: {filename}")
        return filename

    def _scan_evaluation_outputs(self) -> List[Path]:
        """evaluation 출력 디렉토리에서 JSON 파일을 스캔합니다.

        Returns:
            발견된 JSON 파일의 Path 객체 목록

        Raises:
            FileNotFoundError: 출력 디렉토리가 존재하지 않는 경우
        """
        output_dir = Path.cwd() / EVALUATION_OUTPUT_DIR

        if not output_dir.exists():
            raise FileNotFoundError(f"Directory '{EVALUATION_OUTPUT_DIR}' does not exist")

        if not output_dir.is_dir():
            raise NotADirectoryError(f"'{EVALUATION_OUTPUT_DIR}' is not a directory")

        json_files = list(output_dir.glob(EVALUATION_OUTPUT_PATTERN))

        if not json_files:
            print(f"Warning: No JSON files found in '{EVALUATION_OUTPUT_DIR}'")
            return []

        return sorted(json_files)

    def _scan_evaluation_inputs(self) -> List[Path]:
        """evaluation_input 디렉토리에서 JSON 파일을 스캔합니다.

        Returns:
            발견된 입력 JSON 파일의 Path 객체 목록
        """
        from .constants import EVALUATION_INPUT_DIR
        input_dir = Path.cwd() / EVALUATION_INPUT_DIR

        if not input_dir.exists() or not input_dir.is_dir():
            return []

        return list(input_dir.glob("input_*.json"))

    def _extract_trace_data_from_input(self, input_file: Path) -> Optional[Dict[str, Any]]:
        """입력 파일을 파싱하고 trace 레벨 정보를 추출합니다.

        Args:
            input_file: 입력 JSON 파일 경로

        Returns:
            trace 데이터를 포함하는 딕셔너리 또는 추출 실패 시 None
        """
        try:
            with open(input_file, "r", encoding=DEFAULT_FILE_ENCODING) as f:
                spans = json.load(f)

            if not isinstance(spans, list) or not spans:
                return None

            # 첫 번째 span에서 session_id와 trace_id 추출
            first_span = spans[0]
            session_id = first_span.get("attributes", {}).get("session.id")
            trace_id = first_span.get("traceId")

            if not session_id or not trace_id:
                return None

            # 입력/출력 메시지 추출
            input_messages = []
            output_messages = []
            tools_used = []

            for span in spans:
                body = span.get("body", {})

                # 입력 메시지 추출
                if "input" in body and isinstance(body["input"], dict):
                    messages = body["input"].get("messages", [])
                    for msg in messages:
                        if isinstance(msg, dict):
                            input_messages.append(msg)

                # 출력 메시지 추출
                if "output" in body and isinstance(body["output"], dict):
                    messages = body["output"].get("messages", [])
                    for msg in messages:
                        if isinstance(msg, dict):
                            output_messages.append(msg)

                            # 메시지 content에서 tool 정보 추출
                            content = msg.get("content", {})
                            if isinstance(content, dict):
                                message_str = content.get("message", "")
                            elif isinstance(content, str):
                                message_str = content
                            else:
                                message_str = ""

                            # content에서 toolUse 찾기
                            if "toolUse" in message_str:
                                try:
                                    # content가 이중 인코딩된 JSON일 수 있음
                                    parsed = json.loads(message_str) if message_str.startswith("[") else None
                                    if isinstance(parsed, list):
                                        for item in parsed:
                                            if isinstance(item, dict) and "toolUse" in item:
                                                tool_name = item["toolUse"].get("name")
                                                if tool_name:
                                                    tools_used.append(tool_name)
                                except (json.JSONDecodeError, TypeError):
                                    pass

            # 고유한 tool과 사용 횟수 집계
            tools_with_counts = {}
            for tool in tools_used:
                tools_with_counts[tool] = tools_with_counts.get(tool, 0) + 1

            # 이 trace의 타임스탬프 추출
            timestamps = [span.get("timeUnixNano") for span in spans if span.get("timeUnixNano")]
            min_timestamp = min(timestamps) if timestamps else None
            max_timestamp = max(timestamps) if timestamps else None

            # span에서 token 사용량 추출
            total_input_tokens = 0
            total_output_tokens = 0

            for span in spans:
                attrs = span.get("attributes", {})
                total_input_tokens += attrs.get("gen_ai.usage.input_tokens", 0)
                total_output_tokens += attrs.get("gen_ai.usage.output_tokens", 0)

            # 타임스탬프가 있으면 latency를 밀리초로 계산
            latency_ms = None
            if min_timestamp and max_timestamp:
                latency_ms = (max_timestamp - min_timestamp) / 1_000_000  # 나노초를 밀리초로 변환

            return {
                "session_id": session_id,
                "trace_id": trace_id,
                "input_messages": input_messages,
                "output_messages": output_messages,
                "tools_used": tools_with_counts,
                "span_count": len(spans),
                "timestamp": min_timestamp,
                "timestamp_end": max_timestamp,
                "latency_ms": latency_ms,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
            }

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse input file {input_file.name}: {e}")
            return None
        except Exception as e:
            print(f"Warning: Error extracting trace data from {input_file.name}: {e}")
            return None

    def _match_input_output_files(
        self,
        output_files: List[Path],
        input_files: List[Path]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """출력 파일을 입력 파일과 매칭하고 trace 데이터를 추출합니다.

        Args:
            output_files: evaluation 출력 파일 경로 목록
            input_files: evaluation 입력 파일 경로 목록

        Returns:
            (session_id, trace_id) 튜플을 trace 데이터에 매핑하는 딕셔너리
        """
        # (session_id, trace_id)를 키로 하는 입력 데이터 맵 구성
        trace_data_map = {}

        for input_file in input_files:
            trace_data = self._extract_trace_data_from_input(input_file)
            if trace_data:
                key = (trace_data["session_id"], trace_data["trace_id"])
                trace_data_map[key] = trace_data

        return trace_data_map

    def _aggregate_evaluation_data(self, json_files: List[Path]) -> List[Dict[str, Any]]:
        """JSON 파일에서 evaluation 데이터를 session_id별로 trace 레벨 세부 정보와 함께 집계합니다.

        Args:
            json_files: 처리할 JSON 파일 경로 목록

        Returns:
            trace 레벨 정보를 포함하는 집계된 세션 데이터 딕셔너리 목록
        """
        sessions_map = {}
        skipped_files = []

        # 입력 파일 스캔 및 trace 데이터 추출
        input_files = self._scan_evaluation_inputs()
        trace_data_map = self._match_input_output_files(json_files, input_files)

        print(f"Found {len(input_files)} input file(s) with trace data")

        for json_file in json_files:
            try:
                with open(json_file, "r", encoding=DEFAULT_FILE_ENCODING) as f:
                    data = json.load(f)
                    session_id = data.get("session_id")

                    if not session_id:
                        skipped_files.append((json_file.name, "No session_id found"))
                        continue

                    if session_id not in sessions_map:
                        sessions_map[session_id] = {
                            "session_id": session_id,
                            "results": [],
                            "metadata": data.get("metadata", {}),
                            "source_files": [],
                            "evaluation_runs": 0,
                            "traces": {}  # trace_id를 trace 데이터에 매핑
                        }

                    # 실제 결과가 있는 경우에만 카운트 증가
                    results = data.get("results", [])
                    if results:
                        sessions_map[session_id]["results"].extend(results)
                        sessions_map[session_id]["evaluation_runs"] += 1

                        # 결과를 trace_id별로 그룹화
                        for result in results:
                            context = result.get("context", {})
                            span_context = context.get("spanContext", {})
                            trace_id = span_context.get("traceId")

                            if trace_id:
                                # trace 항목 가져오기 또는 생성
                                if trace_id not in sessions_map[session_id]["traces"]:
                                    # 입력 파일에서 trace 데이터 가져오기 시도
                                    trace_key = (session_id, trace_id)
                                    trace_data = trace_data_map.get(trace_key, {})

                                    sessions_map[session_id]["traces"][trace_id] = {
                                        "trace_id": trace_id,
                                        "session_id": session_id,
                                        "results": [],
                                        "input": trace_data.get("input_messages", []),
                                        "output": trace_data.get("output_messages", []),
                                        "tools_used": trace_data.get("tools_used", {}),
                                        "span_count": trace_data.get("span_count", 0),
                                        "timestamp": trace_data.get("timestamp"),
                                        "latency_ms": trace_data.get("latency_ms"),
                                        "input_tokens": trace_data.get("input_tokens", 0),
                                        "output_tokens": trace_data.get("output_tokens", 0),
                                        "total_tokens": trace_data.get("total_tokens", 0),
                                    }

                                # 이 trace에 결과 추가
                                sessions_map[session_id]["traces"][trace_id]["results"].append(result)

                    sessions_map[session_id]["source_files"].append(json_file.name)

                    # 메타데이터 병합 (나중 파일이 이전 파일을 덮어씀)
                    if data.get("metadata"):
                        sessions_map[session_id]["metadata"].update(data.get("metadata", {}))

            except json.JSONDecodeError as e:
                skipped_files.append((json_file.name, f"JSON decode error: {e}"))
            except PermissionError as e:
                skipped_files.append((json_file.name, f"Permission denied: {e}"))
            except Exception as e:
                skipped_files.append((json_file.name, f"Error: {e}"))

        # 각 세션의 traces dict를 list로 변환
        for session in sessions_map.values():
            session["traces"] = list(session["traces"].values())

        # 건너뛴 파일 보고
        if skipped_files:
            print(f"Warning: Skipped {len(skipped_files)} file(s):")
            for filename, reason in skipped_files:
                print(f"  - {filename}: {reason}")

        return list(sessions_map.values())

    def _write_dashboard_data(self, evaluation_data: List[Dict[str, Any]]) -> Path:
        """집계된 evaluation 데이터를 dashboard_data.js 파일에 작성합니다.

        Args:
            evaluation_data: 집계된 세션 데이터 목록

        Returns:
            생성된 dashboard_data.js 파일 경로

        Raises:
            IOError: 파일 쓰기 실패 시
        """
        # JavaScript 파일로 데이터 내보내기
        js_content = f"""// Auto-generated dashboard data
// Generated from {EVALUATION_OUTPUT_DIR} directory
// Sessions aggregated by session_id

const EVALUATION_DATA = {json.dumps(evaluation_data, indent=2)};

// Export for use in dashboard
if (typeof window !== 'undefined') {{
    window.EVALUATION_DATA = EVALUATION_DATA;
}}
"""

        dashboard_data_path = Path.cwd() / DASHBOARD_DATA_FILE

        try:
            with open(dashboard_data_path, "w", encoding=DEFAULT_FILE_ENCODING) as f:
                f.write(js_content)
        except PermissionError as e:
            raise IOError(f"Permission denied writing to {DASHBOARD_DATA_FILE}: {e}") from e
        except Exception as e:
            raise IOError(f"Failed to write {DASHBOARD_DATA_FILE}: {e}") from e

        return dashboard_data_path

    def _open_dashboard_in_browser(self, dashboard_html_path: Path) -> bool:
        """기본 브라우저에서 대시보드 HTML 파일을 엽니다.

        Args:
            dashboard_html_path: 대시보드 HTML 파일 경로

        Returns:
            브라우저가 성공적으로 열린 경우 True, 그렇지 않으면 False
        """
        if not dashboard_html_path.exists():
            print(f"Warning: {DASHBOARD_HTML_FILE} not found at {dashboard_html_path}")
            return False

        try:
            # 크로스 플랫폼 file:// URL 처리를 위해 as_uri() 사용
            dashboard_url = dashboard_html_path.as_uri()
            success = webbrowser.open(dashboard_url)

            if success:
                print(f"Opening dashboard in browser: {dashboard_html_path.name}")
                return True
            else:
                print("Warning: Could not open browser automatically.")
                print(f"Please open manually: {dashboard_url}")
                return False

        except Exception as e:
            print(f"Warning: Failed to open browser: {e}")
            print(f"Please open {DASHBOARD_HTML_FILE} manually")
            return False

    def _create_dashboard(self) -> None:
        """대시보드 데이터를 생성하고 브라우저에서 대시보드를 엽니다.

        이 메서드는 evaluation_output/ 디렉토리의 모든 evaluation 출력을 집계하고,
        dashboard_data.js 파일을 생성하며, 기본 브라우저에서 대시보드 HTML을 엽니다.

        참고: 현재 세션의 evaluation뿐만 아니라 디렉토리의 모든 evaluation 출력 파일을 집계합니다.

        Raises:
            FileNotFoundError: evaluation_output 디렉토리가 존재하지 않는 경우
            IOError: 대시보드 데이터 파일을 작성할 수 없는 경우
        """
        try:
            # Step 1: Scan for JSON files
            json_files = self._scan_evaluation_outputs()

            if not json_files:
                print("No evaluation outputs to aggregate for dashboard")
                return

            print(f"Found {len(json_files)} evaluation output file(s)")

            # Step 2: Aggregate data
            evaluation_data = self._aggregate_evaluation_data(json_files)

            if not evaluation_data:
                print("No valid evaluation data found to generate dashboard")
                return

            # Step 3: Write dashboard data file
            dashboard_data_path = self._write_dashboard_data(evaluation_data)

            total_evaluations = sum(len(session.get("results", [])) for session in evaluation_data)
            print(
                f"Dashboard data generated: {len(evaluation_data)} session(s), " f"{total_evaluations} evaluation(s)"
            )

            # Step 4: Open dashboard in browser
            dashboard_html_path = Path.cwd() / DASHBOARD_HTML_FILE
            self._open_dashboard_in_browser(dashboard_html_path)

        except FileNotFoundError as e:
            print(f"Dashboard creation failed: {e}")
            print("Make sure you have run evaluations with auto_save_output=True")
        except IOError as e:
            print(f"Dashboard creation failed: {e}")
        except Exception as e:
            print(f"Unexpected error creating dashboard: {e}")

    def evaluate(
        self, evaluator_id: str, session_spans: List[Dict[str, Any]], evaluation_target: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """변환된 span으로 evaluation API를 호출합니다.

        Args:
            evaluator_id: 단일 evaluator 식별자
            session_spans: OpenTelemetry 형식의 span 문서 목록
            evaluation_target: 평가할 spanIds 또는 traceIds를 포함하는 선택적 dict

        Returns:
            evaluationResults를 포함하는 원시 API 응답

        Raises:
            RuntimeError: API 호출 실패 시
        """
        request = EvaluationRequest(
            evaluator_id=evaluator_id, session_spans=session_spans, evaluation_target=evaluation_target
        )

        evaluator_id_param, request_body = request.to_api_request()

        try:
            response = self.client.evaluate(evaluatorId=evaluator_id_param, **request_body)
            return response
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise RuntimeError(f"Evaluation API error ({error_code}): {error_msg}") from e

    def evaluate_session(
        self,
        session_id: str,
        evaluator_ids: List[str],
        agent_id: str,
        region: str,
        scope: str,
        trace_id: Optional[str] = None,
        span_filter: Optional[Dict[str, str]] = None,
        auto_save_input: bool = False,
        auto_save_output: bool = False,
        auto_create_dashboard: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvaluationResults:
        """하나 이상의 evaluator를 사용하여 세션을 평가합니다.

        Args:
            session_id: 평가할 Session ID
            evaluator_ids: evaluator 식별자 목록 (예: ["Builtin.Helpfulness"])
            agent_id: 세션 데이터를 가져오기 위한 Agent ID
            region: ObservabilityClient를 위한 AWS 리전
            scope: Evaluation scope - "session", "trace", 또는 "span"
            trace_id: trace scope를 위한 Trace ID (선택사항)
            span_filter: span scope를 위한 필터 (선택적 dict, 예: {"tool_name": "calculate_bmi"})
            auto_save_input: True인 경우, 입력 span을 evaluation_input/ 폴더에 저장
            auto_save_output: True인 경우, 결과를 evaluation_output/ 폴더에 저장
            auto_create_dashboard: True인 경우, 모든 evaluation 출력을 집계하고,
                dashboard_data.js를 생성하며, 브라우저에서 대시보드를 엽니다. auto_save_output=True 필요.
                참고: 현재 세션뿐만 아니라 디렉토리의 모든 evaluation 출력을 집계합니다.
            metadata: 실험, 설명 등을 추적하기 위한 선택적 메타데이터 dict

        Returns:
            evaluation 결과를 포함하는 EvaluationResults

        Raises:
            RuntimeError: 세션 데이터를 가져올 수 없거나 evaluation이 실패한 경우
            ValueError: scope-evaluator 조합이 유효하지 않거나 필요한 ID가 누락된 경우
        """
        # evaluator_ids가 비어있지 않은지 검증
        if not evaluator_ids:
            raise ValueError("evaluator_ids cannot be empty")

        # 모든 evaluator에 대해 scope 검증
        for evaluator_id in evaluator_ids:
            self._validate_scope_compatibility(evaluator_id, scope)

        trace_data = self._fetch_session_data(session_id, agent_id, region)

        num_traces = len(trace_data.get_trace_ids())
        num_spans = len(trace_data.spans)
        print(f"Found {num_spans} spans across {num_traces} traces in session")

        # scope가 "span"인 경우 span ID 자동 검색
        span_ids = None
        if scope == "span":
            tool_name_filter = (span_filter or {}).get("tool_name")
            span_ids = trace_data.get_tool_execution_spans(tool_name_filter=tool_name_filter)

            if not span_ids:
                filter_msg = f" (filter: tool_name={tool_name_filter})" if tool_name_filter else ""
                raise ValueError(f"No tool execution spans found in session{filter_msg}")

            print(f"Found {len(span_ids)} tool execution spans for evaluation")

        # scope에 따라 evaluation target 구성
        evaluation_target = self._build_evaluation_target(scope=scope, trace_id=trace_id, span_ids=span_ids)

        if evaluation_target:
            target_type = "traceIds" if "traceIds" in evaluation_target else "spanIds"
            target_ids = evaluation_target[target_type]
            print(f"Evaluation target: {target_type} = {target_ids}")

        print(f"Collecting most recent {DEFAULT_MAX_EVALUATION_ITEMS} relevant items")
        otel_spans = self._get_most_recent_session_spans(trace_data, max_items=DEFAULT_MAX_EVALUATION_ITEMS)

        if not otel_spans:
            print("Warning: No relevant items found after filtering")

        spans_count, logs_count, genai_spans = self._count_span_types(otel_spans)
        print(
            f"Sending {len(otel_spans)} items "
            f"({spans_count} spans [{genai_spans} with gen_ai attrs], "
            f"{logs_count} log events) to evaluation API"
        )

        # 요청 시 입력 저장 (API로 전송되는 span만)
        if auto_save_input:
            self._save_input(session_id, otel_spans)

        results = EvaluationResults(session_id=session_id, metadata=metadata)

        for evaluator_id in evaluator_ids:
            try:
                response = self.evaluate(
                    evaluator_id=evaluator_id, session_spans=otel_spans, evaluation_target=evaluation_target
                )

                api_results = response.get("evaluationResults", [])

                if not api_results:
                    print(f"Warning: Evaluator {evaluator_id} returned no results")

                for api_result in api_results:
                    result = EvaluationResult.from_api_response(api_result)
                    results.add_result(result)

            except Exception as e:
                error_result = EvaluationResult(
                    evaluator_id=evaluator_id,
                    evaluator_name=evaluator_id,
                    evaluator_arn="",
                    explanation=f"Evaluation failed: {str(e)}",
                    context={"spanContext": {"sessionId": session_id}},
                    error=str(e),
                )
                results.add_result(error_result)

        # results.input_data = {"spans": otel_spans} # 나중에 추가 여부 고려

        # 요청 시 출력 저장
        if auto_save_output:
            self._save_output(results)

        # 요청 시 대시보드 생성
        if auto_create_dashboard:
            if auto_save_output:
                self._create_dashboard()
            else:
                print("Warning: auto_create_dashboard requires auto_save_output=True")
                print("Dashboard not created. Set auto_save_output=True to enable dashboard generation.")

        return results
