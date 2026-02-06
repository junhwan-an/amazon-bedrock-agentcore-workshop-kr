# Amazon Bedrock AgentCore SDK Tools 예제

이 폴더는 Amazon Bedrock AgentCore SDK tool 사용을 보여주는 예제를 포함합니다:

## Browser Tools

* `browser_viewer_replay.py` - 적절한 디스플레이 크기 지원을 갖춘 Amazon Bedrock AgentCore Browser Live Viewer.
* `browser_interactive_session.py` - 라이브 뷰잉, 녹화 및 재생 기능을 갖춘 완전한 엔드투엔드 브라우저 경험.
* `session_replay_viewer.py` - 녹화된 브라우저 세션을 재생하기 위한 뷰어.
* `view_recordings.py` - S3에서 녹화된 세션을 보기 위한 독립 실행형 스크립트.

## 사전 요구사항

### Python 의존성
```bash
# requirements.txt에 정의된 모든 패키지 설치
pip install -r requirements.txt
```

필수 패키지: fastapi, uvicorn, rich, boto3, bedrock-agentcore

### AWS Credentials
AWS credentials가 구성되어 있는지 확인하세요:
```bash
# AWS CLI 인증 정보 설정 (access key, secret key, region 입력)
aws configure
```

## 예제 실행하기

### 녹화 및 재생 기능을 갖춘 완전한 브라우저 경험
`02-Agent-Core-browser-tool/interactive_tools` 디렉토리에서:
```bash
python -m live_view_sessionreplay.browser_interactive_session
```

### 녹화 보기
`02-Agent-Core-browser-tool/interactive_tools` 디렉토리에서:
```bash
# S3 버킷에서 녹화된 세션 재생 (YOUR_BUCKET과 YOUR_PREFIX를 실제 값으로 변경)
python -m live_view_sessionreplay.view_recordings --bucket YOUR_BUCKET --prefix YOUR_PREFIX
```

## 녹화 및 재생 기능을 갖춘 완전한 브라우저 경험

라이브 브라우저 뷰잉, S3로의 자동 녹화 및 통합 세션 재생을 포함하는 완전한 엔드투엔드 워크플로우를 실행합니다.

### 기능
- S3로의 자동 녹화 기능을 갖춘 브라우저 세션 생성
- 인터랙티브 제어(take/release)를 갖춘 라이브 뷰
- 실시간으로 디스플레이 해상도 조정
- S3로의 자동 세션 녹화
- 녹화를 시청하기 위한 통합 세션 재생 뷰어

### 작동 방식
1. 스크립트가 녹화 기능이 활성화된 브라우저를 생성합니다
2. 브라우저 세션이 시작되고 로컬 브라우저에 표시됩니다
3. 브라우저를 수동으로 제어하거나 자동화를 실행할 수 있습니다
4. 모든 작업이 자동으로 S3에 녹화됩니다
5. 세션을 종료한 후(Ctrl+C), 녹화를 보여주는 재생 뷰어가 열립니다

### 환경 변수
- `AWS_REGION` - AWS 리전 (기본값: us-west-2)
- `AGENTCORE_ROLE_ARN` - 브라우저 실행을 위한 IAM role ARN (기본값: 계정 ID에서 자동 생성)
- `RECORDING_BUCKET` - 녹화를 위한 S3 버킷 (기본값: session-record-test-{ACCOUNT_ID})
- `RECORDING_PREFIX` - 녹화를 위한 S3 prefix (기본값: replay-data)

### 필수 IAM 권한
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket",
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::session-record-test-*",
                "arn:aws:s3:::session-record-test-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "bedrock:*",
            "Resource": "*"
        }
    ]
}
```

## 독립 실행형 세션 재생 뷰어

새 브라우저를 생성하지 않고 S3에서 직접 녹화된 브라우저 세션을 보기 위한 별도의 도구입니다.

### 기능
- S3에 직접 연결하여 녹화 보기
- 세션 ID를 지정하여 과거 녹화 보기
- 세션 ID가 제공되지 않으면 자동으로 최신 녹화 찾기

### 사용법

```bash
# 버킷에서 최신 녹화 보기
python -m live_view_sessionreplay.view_recordings --bucket session-record-test-123456789012 --prefix replay-data

# 특정 녹화 보기 (session ID 지정)
python -m live_view_sessionreplay.view_recordings --bucket session-record-test-123456789012 --prefix replay-data --session 01JZVDG02M8MXZY2N7P3PKDQ74

# 특정 AWS profile 사용 (~/.aws/credentials의 profile 이름 지정)
python -m live_view_sessionreplay.view_recordings --bucket session-record-test-123456789012 --prefix replay-data --profile my-profile
```

### 녹화 찾기

S3 녹화 목록:
```bash
# S3 버킷의 모든 녹화 파일 목록 조회
aws s3 ls s3://session-record-test-123456789012/replay-data/ --recursive
```

## 문제 해결

### DCV SDK를 찾을 수 없음
DCV SDK 파일이 `interactive_tools/static/dcvjs/`에 배치되어 있는지 확인하세요

### 브라우저 세션이 보이지 않음
- DCV SDK가 올바르게 설치되었는지 확인하세요
- 브라우저 콘솔(F12)에서 오류를 확인하세요
- AWS credentials에 적절한 권한이 있는지 확인하세요

### 녹화가 작동하지 않음
- S3 버킷이 존재하고 접근 가능한지 확인하세요
- S3 작업에 대한 IAM 권한을 확인하세요
- 실행 role에 적절한 권한이 있는지 확인하세요

### 세션 재생 문제
- S3에 녹화가 존재하는지 확인하세요 (AWS CLI 또는 콘솔 사용)
- 콘솔 로그에서 오류를 확인하세요
- S3 버킷 정책이 객체 읽기를 허용하는지 확인하세요

### S3 접근 오류
- AWS credentials가 구성되어 있는지 확인하세요
- S3 작업에 대한 IAM 권한을 확인하세요
- 버킷 이름이 전역적으로 고유한지 확인하세요

## 아키텍처 노트
- 라이브 뷰어는 FastAPI를 사용하여 사전 서명된 DCV URL을 제공합니다
- 녹화는 데이터 플레인의 브라우저 서비스에서 직접 처리됩니다
- 재생은 녹화된 이벤트의 재생을 위해 rrweb-player를 사용합니다
- 모든 컴포넌트는 함께 또는 독립적으로 작동할 수 있습니다