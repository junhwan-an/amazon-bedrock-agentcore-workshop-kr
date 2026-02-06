"""Online evaluation helper functions for agent invocation and evaluation workflows."""

import json
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .evaluation_client import EvaluationClient


def generate_session_id() -> str:
    """Generate a valid session ID in UUID format.

    Returns:
        UUID v4 string (e.g., 'de45c51c-27c3-4670-aa72-c8b302b23890')
    """
    return str(uuid.uuid4())


def invoke_agent(
    agentcore_client: Any,
    agent_arn: str,
    prompt: str,
    session_id: str = '',
    qualifier: str = "DEFAULT"
) -> Tuple[str, List[str]]:
    """Invoke agent runtime and return session ID with response content.

    Args:
        agentcore_client: Boto3 agentcore client
        agent_arn: Agent runtime ARN
        prompt: 사용자 입력 프롬프트
        session_id: 멀티턴 대화를 위한 선택적 session ID (UUID 형식)
                   - 빈 문자열 '' = 새 세션 생성
                   - 유효한 UUID = 기존 세션 계속 또는 특정 세션 ID 사용
        qualifier: Agent runtime qualifier (기본값: DEFAULT)

    Returns:
        Tuple of (session_id, content_list)
    """
    api_params = {
        'agentRuntimeArn': agent_arn,
        'qualifier': qualifier,
        'payload': json.dumps({"prompt": prompt})
    }

    # session_id가 제공된 경우에만 파라미터에 추가 (멀티턴 대화 지원)
    if session_id:
        api_params['runtimeSessionId'] = session_id

    boto3_response = agentcore_client.invoke_agent_runtime(**api_params)

    # 응답에서 session ID 추출 (우선순위: HTTP 헤더 > 응답 body > 입력값)
    returned_session_id = (
        boto3_response['ResponseMetadata']['HTTPHeaders'].get('x-amzn-bedrock-agentcore-runtime-session-id')
        or boto3_response.get('runtimeSessionId')
        or session_id
    )

    content = []
    # 스트리밍 응답 처리
    if "text/event-stream" in boto3_response.get("contentType", ""):
        for line in boto3_response["response"].iter_lines(chunk_size=1):
            if line:
                line = line.decode("utf-8")
                # SSE(Server-Sent Events) 형식에서 "data: " 접두사 제거
                if line.startswith("data: "):
                    content.append(line[6:])
    else:
        # 일반 EventStream 응답 처리
        try:
            events = [event for event in boto3_response.get("response", [])]
            if events:
                content = [json.loads(events[0].decode("utf-8"))]
        except Exception as e:
            content = [f"EventStream 읽기 오류: {e}"]

    return returned_session_id, content


def evaluate_session(
    eval_client: EvaluationClient,
    session_id: str,
    evaluators: List[str],
    scope: str,
    agent_id: str,
    region: str,
    experiment_name: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Any:
    """Evaluate a session with specified evaluators.

    Args:
        eval_client: EvaluationClient 인스턴스
        session_id: 평가할 Session ID
        evaluators: Evaluator ID 리스트
        scope: Evaluation 범위 (session, trace, 또는 span)
        agent_id: Agent ID
        region: AWS region
        experiment_name: 추적을 위한 실험 식별자
        metadata: 선택적 메타데이터 딕셔너리

    Returns:
        EvaluationResults 객체
    """
    eval_metadata = {"experiment": experiment_name}
    if metadata:
        eval_metadata.update(metadata)

    results = eval_client.evaluate_session(
        session_id=session_id,
        evaluator_ids=evaluators,
        agent_id=agent_id,
        region=region,
        scope=scope,
        auto_save_input=True,
        auto_save_output=True,
        auto_create_dashboard=True,
        metadata=eval_metadata
    )

    return results


def evaluate_session_comprehensive(
    eval_client: EvaluationClient,
    session_id: str,
    agent_id: str,
    region: str,
    experiment_name: str,
    flexible_evaluators: List[str],
    session_only_evaluators: List[str],
    span_only_evaluators: List[str],
    metadata: Optional[Dict[str, Any]] = None
) -> List[Any]:
    """Run all evaluators across appropriate scopes.

    Args:
        eval_client: EvaluationClient 인스턴스
        session_id: 평가할 Session ID
        agent_id: Agent ID
        region: AWS region
        experiment_name: 실험 식별자
        flexible_evaluators: 유연한 범위 evaluator 리스트
        session_only_evaluators: 세션 전용 evaluator 리스트
        span_only_evaluators: Span 전용 evaluator 리스트
        metadata: 선택적 메타데이터 딕셔너리

    Returns:
        결합된 evaluation 결과 리스트
    """
    all_results = []

    evaluation_configs = [
        {"evaluators": flexible_evaluators, "scope": "session"},
        {"evaluators": session_only_evaluators, "scope": "session"},
        {"evaluators": span_only_evaluators, "scope": "span"}
    ]

    for config in evaluation_configs:
        if config["evaluators"]:
            try:
                results = evaluate_session(
                    eval_client=eval_client,
                    session_id=session_id,
                    evaluators=config["evaluators"],
                    scope=config["scope"],
                    agent_id=agent_id,
                    region=region,
                    experiment_name=experiment_name,
                    metadata=metadata
                )
                all_results.extend(results.results)
            except Exception as e:
                print(f"{config['scope']} evaluation 오류: {e}")

    return all_results


def invoke_and_evaluate(
    agentcore_client: Any,
    eval_client: EvaluationClient,
    agent_arn: str,
    agent_id: str,
    region: str,
    prompt: str,
    experiment_name: str,
    session_id: str = '',
    metadata: Optional[Dict[str, Any]] = None,
    evaluators: Optional[List[str]] = None,
    scope: str = "session",
    delay: int = 90,
    flexible_evaluators: Optional[List[str]] = None,
    session_only_evaluators: Optional[List[str]] = None,
    span_only_evaluators: Optional[List[str]] = None
) -> Tuple[str, List[Any]]:
    """Complete workflow: invoke agent, wait for log propagation, then evaluate.

    Args:
        agentcore_client: Boto3 agentcore client
        eval_client: EvaluationClient 인스턴스
        agent_arn: Agent runtime ARN
        agent_id: Agent ID
        region: AWS region
        prompt: 사용자 입력 프롬프트
        experiment_name: 실험 식별자
        session_id: 선택적 session ID (빈 문자열 = 새 세션, UUID = 세션 계속/지정)
        metadata: 선택적 메타데이터 딕셔너리
        evaluators: Evaluator ID 리스트 (None = 포괄적 evaluation 사용)
        scope: Evaluation 범위 (session, trace, span)
        delay: CloudWatch 전파를 위한 대기 시간(초)
        flexible_evaluators: evaluators가 None인 경우 필수
        session_only_evaluators: evaluators가 None인 경우 필수
        span_only_evaluators: evaluators가 None인 경우 필수

    Returns:
        Tuple of (session_id, results_list)
    """
    returned_session_id, content = invoke_agent(
        agentcore_client=agentcore_client,
        agent_arn=agent_arn,
        prompt=prompt,
        session_id=session_id
    )

    # CloudWatch Logs에 trace 데이터가 전파될 때까지 대기 (evaluation 전 필수)
    time.sleep(delay)

    # evaluators가 None이면 포괄적 evaluation 수행 (여러 scope에 걸쳐)
    if evaluators is None:
        if not all([flexible_evaluators, session_only_evaluators, span_only_evaluators]):
            raise ValueError("포괄적인 evaluation을 위해서는 evaluator 리스트를 제공해야 합니다")

        results = evaluate_session_comprehensive(
            eval_client=eval_client,
            session_id=returned_session_id,
            agent_id=agent_id,
            region=region,
            experiment_name=experiment_name,
            flexible_evaluators=flexible_evaluators,
            session_only_evaluators=session_only_evaluators,
            span_only_evaluators=span_only_evaluators,
            metadata=metadata
        )
    else:
        # 단일 scope evaluation 수행
        eval_results = evaluate_session(
            eval_client=eval_client,
            session_id=returned_session_id,
            evaluators=evaluators,
            scope=scope,
            agent_id=agent_id,
            region=region,
            experiment_name=experiment_name,
            metadata=metadata
        )
        results = eval_results.results

    return returned_session_id, content, results
