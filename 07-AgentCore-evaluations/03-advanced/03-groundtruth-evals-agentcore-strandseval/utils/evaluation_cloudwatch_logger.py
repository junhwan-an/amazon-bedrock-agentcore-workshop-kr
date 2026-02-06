"""원본 trace ID를 사용하는 evaluation 결과용 커스텀 CloudWatch logger.

이 모듈은 AgentCore Observability Dashboard가 기대하는 정확한 EMF 형식을 사용하여
CloudWatch 로깅을 제공하지만, 새로운 trace ID를 생성하는 대신 원본 AgentCore trace
데이터셋의 trace ID를 사용합니다.

strands_evals.telemetry._cloudwatch_logger를 기반으로 하되, case metadata에서
trace_id를 파라미터로 받도록 수정되었습니다.
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

import boto3

logger = logging.getLogger(__name__)

# 모듈 레벨 CloudWatch client (지연 초기화)
_cloudwatch_client = None


def _get_cloudwatch_client():
    """CloudWatch Logs client를 가져오거나 생성합니다 (singleton 패턴)."""
    global _cloudwatch_client
    if _cloudwatch_client is None:
        region = os.environ.get("AWS_REGION", "us-east-1")
        _cloudwatch_client = boto3.client("logs", region_name=region)
    return _cloudwatch_client


@dataclass
class EvaluationLogConfig:
    """Evaluation 로깅을 위한 설정."""
    destination_log_group: str
    log_stream: str
    service_name: str
    resource_log_group: Optional[str] = None

    @classmethod
    def from_environment(cls) -> "EvaluationLogConfig":
        """환경 변수에서 로그 설정을 파싱합니다.

        환경 변수:
        - EVALUATION_RESULTS_LOG_GROUP: 결과 로그 그룹의 기본 이름
        - LOG_STREAM_NAME: 명시적 로그 스트림 이름 (우선순위 높음)
        - OTEL_RESOURCE_ATTRIBUTES: service.name과 선택적으로 aws.log.group.names 포함
        - OTEL_EXPORTER_OTLP_LOGS_HEADERS: x-aws-log-stream 포함 (대체)
        """
        # EVALUATION_RESULTS_LOG_GROUP에서 대상 로그 그룹
        base_log_group = os.environ.get("EVALUATION_RESULTS_LOG_GROUP", "default_strands_evals_results")
        destination_log_group = f"/aws/bedrock-agentcore/evaluations/results/{base_log_group}"

        # 로그 스트림: 먼저 LOG_STREAM_NAME 환경 변수 확인 (명시적 오버라이드)
        log_stream = os.environ.get("LOG_STREAM_NAME", "")

        # 대체: OTEL_EXPORTER_OTLP_LOGS_HEADERS에서 로그 스트림 파싱
        # OpenTelemetry 헤더 형식: "key1=value1,key2=value2"
        if not log_stream:
            logs_headers = os.environ.get("OTEL_EXPORTER_OTLP_LOGS_HEADERS", "")
            if logs_headers:
                for header in logs_headers.split(","):
                    if "=" in header:
                        key, value = header.split("=", 1)
                        if key.strip() == "x-aws-log-stream":
                            log_stream = value.strip()
                            break

        # 최종 대체: "default" 사용
        if not log_stream:
            log_stream = "default"

        # service.name과 aws.log.group.names를 위해 OTEL_RESOURCE_ATTRIBUTES 파싱
        # OpenTelemetry 리소스 속성 형식: "key1=value1,key2=value2"
        resource_attrs = os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "")
        service_name = None
        resource_log_group = None

        for attr in resource_attrs.split(","):
            if "=" in attr:
                key, value = attr.split("=", 1)  # 첫 번째 '='만 분리 (value에 '=' 포함 가능)
                key = key.strip()
                value = value.strip()
                if key == "service.name":
                    service_name = value
                elif key == "aws.log.group.names":
                    resource_log_group = value

        if not service_name:
            raise ValueError("service.name must be set in OTEL_RESOURCE_ATTRIBUTES environment variable")

        return cls(
            destination_log_group=destination_log_group,
            log_stream=log_stream,
            service_name=service_name,
            resource_log_group=resource_log_group,
        )


def send_evaluation_to_cloudwatch(
    trace_id: str,
    session_id: str,
    evaluator_name: str,
    score: float,
    explanation: str,
    evaluation_level: str = "Trace",
    label: Optional[str] = None,
    config_id: str = "strands-offline-evaluation",
) -> bool:
    """Evaluation 결과를 EMF 형식으로 CloudWatch에 전송합니다.

    이 함수는 AgentCore Observability Dashboard가 기대하는 정확한 EMF 형식을 사용하지만,
    원본 AgentCore trace 데이터셋의 trace_id를 사용합니다.

    Args:
        trace_id: AgentCore Observability의 원본 trace ID (case metadata에서 전달됨)
        session_id: 원본 trace 데이터셋의 session ID
        evaluator_name: 전체 evaluator 이름 (예: "Custom.StrandsEvalOfflineTravelEvaluator")
        score: Evaluation 점수 (0.0 ~ 1.0)
        explanation: 점수에 대한 설명
        evaluation_level: "Trace" 또는 "Span" (기본값: "Trace")
        label: 점수 레이블 ("YES", "NO" 또는 커스텀). None이면 점수에서 파생됨.
        config_id: ARN 구성을 위한 설정 ID (기본값: "strands-offline-evaluation")

    Returns:
        로깅 성공 시 True, 실패 시 False
    """
    try:
        config = EvaluationLogConfig.from_environment()

        if not config.destination_log_group:
            logger.warning("No destination log group configured, skipping CloudWatch logging")
            return False

        cloudwatch_client = _get_cloudwatch_client()

        # 로그 그룹이 존재하는지 확인
        try:
            cloudwatch_client.create_log_group(logGroupName=config.destination_log_group)
            logger.info(f"Created log group: {config.destination_log_group}")
        except cloudwatch_client.exceptions.ResourceAlreadyExistsException:
            pass
        except Exception as e:
            logger.warning(f"Failed to create log group: {str(e)}")

        # 로그 스트림이 존재하는지 확인
        try:
            cloudwatch_client.create_log_stream(
                logGroupName=config.destination_log_group,
                logStreamName=config.log_stream
            )
            logger.info(f"Created log stream: {config.log_stream}")
        except cloudwatch_client.exceptions.ResourceAlreadyExistsException:
            pass
        except Exception as e:
            logger.warning(f"Failed to create log stream: {str(e)}")

        # 로그 스트림의 시퀀스 토큰 가져오기
        # CloudWatch Logs는 동시 쓰기 방지를 위해 시퀀스 토큰 사용
        sequence_token = None
        try:
            response = cloudwatch_client.describe_log_streams(
                logGroupName=config.destination_log_group,
                logStreamNamePrefix=config.log_stream
            )
            if response["logStreams"]:
                sequence_token = response["logStreams"][0].get("uploadSequenceToken")
        except Exception as e:
            logger.warning(f"Failed to get sequence token: {str(e)}")

        # 제공되지 않은 경우 점수에서 레이블 파생
        if label is None:
            label = "YES" if score >= 0.5 else "NO"

        # ARN 구성 (bedrock-agentcore 형식 사용)
        region = os.environ.get("AWS_REGION", "us-east-1")
        account_id = os.environ.get("AWS_ACCOUNT_ID", "")
        config_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:online-evaluation-config/{config_id}"
        evaluator_arn = f"arn:aws:bedrock-agentcore:::evaluator/{evaluator_name}"

        # config_id에서 config_name 파생 (예: "EKS_Agent_Evaluation-5MB8aF5rLE"에서 "EKS_Agent_Evaluation")
        config_name = config_id.rsplit("-", 1)[0] if "-" in config_id else config_id

        # 현재 타임스탬프 가져오기
        current_time_ns = time.time_ns()  # nanoseconds (EMF 로그용)
        current_time_ms = int(current_time_ns / 1_000_000)  # milliseconds (CloudWatch 이벤트용)

        # log_data 구성 (EMF 내부에 들어가는 속성들)
        log_data = {
            "gen_ai.evaluation.name": evaluator_name,
            "session.id": session_id,
            "gen_ai.response.id": trace_id,
            "gen_ai.evaluation.score.value": score,
            "gen_ai.evaluation.explanation": explanation or "",
            "gen_ai.evaluation.score.label": label,
            "aws.bedrock_agentcore.online_evaluation_config.arn": config_arn,
            "aws.bedrock_agentcore.online_evaluation_config.name": config_name,
            "aws.bedrock_agentcore.evaluator.arn": evaluator_arn,
            "aws.bedrock_agentcore.evaluator.rating_scale": "Numerical",
            "aws.bedrock_agentcore.evaluation_level": evaluation_level,
        }

        # EMF 로그 구조 구성 (strands_evals의 정확한 형식)
        # EMF (Embedded Metric Format): CloudWatch에서 메트릭과 로그를 함께 전송하는 형식
        emf_log = {
            "resource": {
                "attributes": {
                    "aws.service.type": "gen_ai_agent",
                    "aws.local.service": config.service_name,
                    "service.name": config.service_name,
                }
            },
            "traceId": trace_id,
            "timeUnixNano": current_time_ns,
            "observedTimeUnixNano": current_time_ns,
            "severityNumber": 9,  # OpenTelemetry severity: INFO
            "name": "gen_ai.evaluation.result",
            "attributes": {
                **log_data,
            },
            "onlineEvaluationConfigId": config_id,
            evaluator_name: score,  # metric을 위한 동적 키
            "label": label,
            "service.name": config.service_name,
            "_aws": {
                "Timestamp": current_time_ms,
                "CloudWatchMetrics": [
                    {
                        "Namespace": "Bedrock-AgentCore/Evaluations",
                        "Dimensions": [  # 메트릭을 다양한 차원으로 집계 가능
                            ["service.name"],
                            ["label", "service.name"],
                            ["service.name", "onlineEvaluationConfigId"],
                            ["label", "service.name", "onlineEvaluationConfigId"],
                        ],
                        "Metrics": [{"Name": evaluator_name, "Unit": "None"}],
                    }
                ],
            },
        }

        # CloudWatch로 전송
        log_event = {
            "timestamp": current_time_ms,
            "message": json.dumps(emf_log)
        }

        put_log_params = {
            "logGroupName": config.destination_log_group,
            "logStreamName": config.log_stream,
            "logEvents": [log_event]
        }

        # 시퀀스 토큰이 있으면 추가 (동시 쓰기 방지)
        if sequence_token:
            put_log_params["sequenceToken"] = sequence_token

        cloudwatch_client.put_log_events(**put_log_params)

        logger.info(
            f"Sent evaluation to CloudWatch: trace_id={trace_id[:16]}..., "
            f"evaluator={evaluator_name}, score={score}, label={label}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to send evaluation to CloudWatch: {str(e)}")
        return False


def log_evaluation_batch(
    results: list[dict],
    evaluator_name: str,
    config_id: str = "strands-offline-evaluation",
) -> int:
    """여러 evaluation 결과를 CloudWatch에 전송합니다.

    Args:
        results: 키를 포함하는 dict 리스트: trace_id, session_id, score, explanation, label (선택)
        evaluator_name: 전체 evaluator 이름
        config_id: 설정 ID

    Returns:
        성공적으로 로깅된 결과의 수
    """
    success_count = 0
    for result in results:
        success = send_evaluation_to_cloudwatch(
            trace_id=result["trace_id"],
            session_id=result["session_id"],
            evaluator_name=evaluator_name,
            score=result["score"],
            explanation=result.get("explanation", ""),
            label=result.get("label"),
            config_id=config_id,
        )
        if success:
            success_count += 1

    logger.info(f"Logged {success_count}/{len(results)} evaluation results to CloudWatch")
    return success_count
