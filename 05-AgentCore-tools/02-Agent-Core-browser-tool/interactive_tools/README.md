# Amazon Bedrock Agentcore SDK Tools 예제

이 폴더는 AgentCore SDK tool 사용을 보여주는 예제를 포함합니다:

## Browser Tools

* `browser_viewer.py` - 적절한 디스플레이 크기 지원을 갖춘 Amazon Bedrock Agentcore Browser Live Viewer.
* `run_live_viewer.py` - Bedrock Agentcore Browser Live Viewer를 실행하는 독립 실행형 스크립트.

## Code Interpreter Tools

* `dynamic_research_agent_langgraph.py` - 동적 코드 생성 기능을 갖춘 LangGraph 기반 연구 agent

## 사전 요구사항

### Python 의존성
```bash
# requirements.txt에 정의된 모든 의존성 설치
pip install -r requirements.txt
```

필수 패키지: fastapi, uvicorn, rich, boto3, bedrock-agentcore

### AWS 자격 증명 (S3 스토리지용)
S3 녹화 스토리지를 위해 AWS 자격 증명이 구성되어 있는지 확인하세요:
```bash
# AWS CLI 자격 증명 설정 (access key, secret key, region 입력)
aws configure
```

## 예제 실행

### Browser Live Viewer
`02-Agent-Core-browser-tool` 디렉토리에서:
```bash
# 브라우저 실시간 뷰어 실행 (모듈로 실행)
python -m interactive_tools.run_live_viewer
```

### Dynamic Research Agent
`02-Agent-Core-browser-tool` 디렉토리에서:
```bash
# 동적 코드 생성 기능을 가진 연구 agent 실행
python -m interactive_tools.dynamic_research_agent_langgraph
```

### Bedrock Model 액세스
동적 연구 agent 예제는 Amazon Bedrock의 Claude model을 사용합니다:
- AWS 계정에서 Anthropic Claude model에 대한 액세스가 필요합니다
- 기본 model은 `global.anthropic.claude-haiku-4-5-20251001-v1:0`입니다
- `dynamic_research_agent_langgraph.py`에서 이 줄을 수정하여 model을 변경할 수 있습니다:
  ```python
  # Line 38 in DynamicResearchAgent.__init__()
  self.llm = ChatBedrockConverse(
      model="global.anthropic.claude-haiku-4-5-20251001-v1:0", # <- 원하는 model로 변경
      region_name=region
  )
  ```
- [Amazon Bedrock 콘솔](https://console.aws.amazon.com/bedrock/home#/modelaccess)에서 model 액세스를 요청하세요

### Session Replay
`02-Agent-Core-browser-tool/interactive_tools` 디렉토리에서:
```bash
# 브라우저 세션 재생 실행
python -m live_view_sessionreplay.browser_interactive_session
```

## Browser Live Viewer

Amazon DCV 기술을 사용한 실시간 브라우저 보기 기능.

### 기능

**디스플레이 크기 제어**
- 1280×720 (HD)
- 1600×900 (HD+) - 기본값
- 1920×1080 (Full HD)
- 2560×1440 (2K)

**세션 제어**
- Take Control: 자동화를 비활성화하고 수동으로 상호작용
- Release Control: 자동화로 제어 반환

### 구성
- 커스텀 포트: `BrowserViewerServer(browser_client, port=8080)`

## Browser Session 녹화 및 재생

디버깅, 테스트 및 데모 목적으로 브라우저 세션을 녹화하고 재생합니다.

### 중요한 제한사항
이 tool은 비디오 스트림이 아닌 rrweb을 사용하여 DOM 이벤트를 녹화합니다:
- 실제 브라우저 콘텐츠(DCV 캔버스)는 검은색 상자로 나타날 수 있습니다
- 픽셀 완벽한 비디오 녹화를 위해서는 화면 녹화 소프트웨어를 사용하세요

## 문제 해결

### DCV SDK를 찾을 수 없음
DCV SDK 파일이 `interactive_tools/static/dcvjs/`에 배치되어 있는지 확인하세요

### 브라우저 세션이 보이지 않음
- 브라우저 콘솔(F12)에서 오류를 확인하세요
- AWS 자격 증명에 적절한 권한이 있는지 확인하세요

### 재생 중 녹화를 찾을 수 없음
- 녹화가 저장될 때 표시된 정확한 경로를 확인하세요
- S3 녹화의 경우 전체 S3 URL을 사용하세요
- `aws s3 ls` 또는 `ls` 명령을 사용하여 파일이 존재하는지 확인하세요

### S3 액세스 오류
- AWS 자격 증명이 구성되어 있는지 확인하세요
- S3 작업에 대한 IAM 권한을 확인하세요
- 버킷 이름이 전역적으로 고유한지 확인하세요

## 성능 고려사항
- 녹화는 브라우저 성능에 오버헤드를 추가합니다
- 파일 크기는 일반적으로 분당 1-10MB입니다
- S3 업로드는 녹화가 중지된 후에 발생합니다
- 재생은 전체 파일을 먼저 다운로드해야 합니다

## 아키텍처 참고사항
- Live viewer는 FastAPI를 사용하여 사전 서명된 DCV URL을 제공합니다
- 녹화는 rrweb 라이브러리를 통해 DOM 이벤트를 캡처합니다
- 재생은 rrweb-player를 사용합니다
- 모든 컴포넌트는 동일한 BrowserClient 인스턴스를 공유합니다
- 모듈식 설계로 각 컴포넌트를 독립적으로 사용할 수 있습니다