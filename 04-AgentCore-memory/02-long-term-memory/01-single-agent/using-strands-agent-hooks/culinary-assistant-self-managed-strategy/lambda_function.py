import json
import boto3
import logging
import uuid
import time
from datetime import datetime
from urllib.parse import urlparse

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class NotificationHandler:
    """Handles parsing SQS events and retrieving S3 payloads"""

    def __init__(self):
        self.s3_client = boto3.client("s3")

    def process_sqs_event(self, event):
        """Extract job details from SQS event and download S3 payload"""
        if len(event["Records"]) != 1:
            raise ValueError(f"Expected 1 record, got {len(event['Records'])}")

        # SQS 메시지 파싱
        record = event["Records"][0]
        message = json.loads(record["body"])
        sqs_message = json.loads(message["Message"])

        logger.info(f"Received message: {json.dumps(sqs_message)}")

        # 작업 메타데이터 추출
        job_metadata = {
            "job_id": sqs_message["jobId"],
            "memory_id": sqs_message["memoryId"],
            "strategy_id": sqs_message["strategyId"],
            "s3_location": sqs_message["s3PayloadLocation"],
        }

        # payload 다운로드 및 파싱
        payload = self._download_payload(job_metadata["s3_location"])

        return job_metadata, payload

    def _download_payload(self, s3_location):
        """Download payload from S3 location"""
        # S3 URI를 bucket과 key로 파싱 (예: s3://bucket-name/path/to/file)
        parsed_url = urlparse(s3_location)
        bucket = parsed_url.netloc
        key = parsed_url.path.lstrip("/")  # 앞의 '/' 제거

        logger.info(f"Downloading payload from bucket: {bucket}, key: {key}")

        response = self.s3_client.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read())


class MemoryExtractor:
    """Extracts memory records from conversation payload"""

    def __init__(self, model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0"):
        self.bedrock_client = boto3.client("bedrock-runtime")
        self.model_id = model_id

    def extract_memories(self, payload):
        """Extract memories from conversation payload using Bedrock model"""
        conversation_text = self._build_conversation_text(payload)

        # LLM에게 대화에서 사용자 정보를 추출하도록 요청하는 프롬프트
        prompt = f"""Extract user preferences, interests, and facts from this conversation.
Return ONLY a valid JSON array with this format:
[{{"content": "detailed description", "type": "preference|interest|fact", "confidence": 0.0-1.0}}]

Focus on extracting specific, meaningful pieces of information that would be useful to remember.
Conversation:
{conversation_text}"""

        # Bedrock Claude 모델 호출을 위한 요청 구조
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{"role": "user", "content": prompt}],
        }

        try:
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id, body=json.dumps(request_body)
            )

            response_body = json.loads(response["body"].read())
            extracted_text = response_body["content"][0]["text"]

            # LLM 응답에서 JSON 배열 부분만 추출 (텍스트 설명 제외)
            start_idx = extracted_text.find("[")
            end_idx = extracted_text.rfind("]") + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = extracted_text[start_idx:end_idx]
                extracted_data = json.loads(json_str)
                logger.info(f"Extracted {len(extracted_data)} memories")
                return self._format_extracted_memories(extracted_data, payload)
            else:
                logger.error("Could not find JSON in model response")
                return []

        except Exception as e:
            logger.error(f"Error extracting memories: {str(e)}")
            return []

    def _build_conversation_text(self, payload):
        """Build formatted conversation text from payload"""
        text = ""

        # 사용 가능한 경우 과거 컨텍스트 포함
        if "historicalContext" in payload:
            text += "Previous conversation:\n"
            for msg in payload["historicalContext"]:
                if "role" in msg and "content" in msg and "text" in msg["content"]:
                    text += f"{msg['role']}: {msg['content']['text']}\n"

        # 현재 컨텍스트 추가
        if "currentContext" in payload:
            text += "\nCurrent conversation:\n"
            for msg in payload["currentContext"]:
                if "role" in msg and "content" in msg and "text" in msg["content"]:
                    text += f"{msg['role']}: {msg['content']['text']}\n"

        return text

    def _format_extracted_memories(self, extracted_data, payload):
        """Format extracted memories with metadata"""
        memories = []
        session_id = payload.get("sessionId", "unknown-session")
        actor_id = payload.get("actorId", "unknown-actor")

        # payload에서 타임스탬프 가져오거나 현재 시간 사용
        timestamp = payload.get("endingTimestamp", int(time.time()))

        for item in extracted_data:
            if (
                not isinstance(item, dict)
                or "content" not in item
                or "type" not in item
            ):
                logger.warning(f"Skipping invalid memory item: {item}")
                continue

            # namespace는 메모리를 계층적으로 구조화하는 경로
            # 형식: /interests/actor/{actorId}/session/{sessionId}
            namespace = f"/interests/actor/{actor_id}/session/{session_id}/"

            memory = {
                "content": item["content"],
                "namespaces": [namespace],
                "memoryStrategyId": None,  # batch_ingest_memories에서 설정됨
                "timestamp": timestamp,
            }

            logger.info(f"Extracted memory with namespace: {namespace}")
            logger.info(f"Extracted memory: {memory}")

            memories.append(memory)

        return memories


class MemoryIngestor:
    """Ingests extracted memories back into AgentCore"""

    def __init__(self):
        self.agentcore_client = boto3.client("bedrock-agentcore")

    def batch_ingest_memories(self, memory_id, memory_records, strategy_id):
        """Ingest memory records using AgentCore batch API"""
        if not memory_records:
            logger.info("No memory records to ingest")
            return {"recordsIngested": 0}

        # 모든 레코드에 대해 strategy ID 설정
        for record in memory_records:
            record["memoryStrategyId"] = strategy_id

        # AgentCore batch API 형식에 맞게 레코드 변환
        batch_records = []
        for record in memory_records:
            batch_record = {
                "requestIdentifier": str(uuid.uuid4()),
                "content": {"text": record["content"]},
                "namespaces": record["namespaces"],
                "memoryStrategyId": record["memoryStrategyId"],
            }

            # 제공된 경우 타임스탬프 추가 - 밀리초 타임스탬프 처리
            if "timestamp" in record:
                try:
                    ts_value = record["timestamp"]

                    # 타임스탬프가 밀리초 단위인지 확인 (13자리 숫자)
                    if (
                        isinstance(ts_value, int) and ts_value > 10000000000
                    ):  # 100억 이상 = 밀리초
                        # 밀리초를 초로 변환
                        ts_seconds = ts_value / 1000.0
                        batch_record["timestamp"] = datetime.fromtimestamp(ts_seconds)
                        logger.info(
                            f"Converted millisecond timestamp to datetime: {batch_record['timestamp']}"
                        )
                    else:
                        # 일반 Unix 타임스탬프로 처리
                        batch_record["timestamp"] = datetime.fromtimestamp(ts_value)
                except Exception as e:
                    logger.error(
                        f"Error processing timestamp {record['timestamp']}: {str(e)}"
                    )
                    # 대체 시간으로 현재 시간 사용
                    batch_record["timestamp"] = datetime.now()
                    logger.info(
                        f"Using fallback timestamp: {batch_record['timestamp']}"
                    )

            batch_records.append(batch_record)

        # AgentCore에 배치 생성 실행
        try:
            logger.info(f"Ingesting {len(batch_records)} memory records")

            self.agentcore_client.batch_create_memory_records(
                memoryId=memory_id, records=batch_records, clientToken=str(uuid.uuid4())
            )

            logger.info(f"Successfully ingested {len(batch_records)} memory records")
            return {"recordsIngested": len(batch_records)}

        except Exception as e:
            logger.error(f"Failed to ingest memory records: {str(e)}")
            raise


def lambda_handler(event, context):
    """Main Lambda handler orchestrating the memory processing pipeline"""

    # 컴포넌트 초기화
    notification_handler = NotificationHandler()
    extractor = MemoryExtractor()
    ingestor = MemoryIngestor()

    try:
        # 1. SQS 이벤트 처리 및 S3에서 payload 다운로드
        job_metadata, payload = notification_handler.process_sqs_event(event)
        logger.info(
            f"Processing job {job_metadata['job_id']} for memory {job_metadata['memory_id']}"
        )

        # 2. Bedrock model을 사용하여 대화에서 메모리 추출
        extracted_memories = extractor.extract_memories(payload)
        logger.info(f"Extracted {len(extracted_memories)} memories")

        # 3. 추출된 메모리를 AgentCore에 저장
        if extracted_memories:
            ingest_result = ingestor.batch_ingest_memories(
                job_metadata["memory_id"],
                extracted_memories,
                job_metadata["strategy_id"],
            )

            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "jobId": job_metadata["job_id"],
                        "extractedMemories": len(extracted_memories),
                        "ingestedRecords": ingest_result["recordsIngested"],
                    }
                ),
            }
        else:
            logger.info("No memories extracted, nothing to ingest")
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "jobId": job_metadata["job_id"],
                        "extractedMemories": 0,
                        "ingestedRecords": 0,
                    }
                ),
            }

    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
