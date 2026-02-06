# AgentCore Policy - 시작하기 데모

Amazon Bedrock AgentCore Policy를 사용하여 AI agent에 대한 정책 기반 제어를 구현하는 완전한 실습 데모입니다.

## 🚀 빠른 시작

1. **의존성 설치**: `pip install -r requirements.txt`
2. **노트북 열기**: `jupyter notebook AgentCore-Policy-Demo.ipynb`
3. **노트북의 단계를 따라하기**

> **참고**: 네이티브 policy-registry API 지원을 위해 boto3 버전 1.42.0 이상이 필요합니다.

## 개요

이 데모는 AgentCore Gateway를 통해 AI agent와 tool 간의 상호작용에 대한 정책 기반 제어를 구현하는 완전한 안내를 제공합니다.

## 학습 내용

- ✅ Lambda 함수를 agent tool로 배포
- ✅ 여러 Lambda 대상으로 AgentCore Gateway 설정
- ✅ Policy Engine 생성 및 구성
- ✅ 세밀한 액세스 제어를 위한 Cedar 정책 작성
- ✅ 실제 AI agent 요청으로 정책 적용 테스트
- ✅ ALLOW 및 DENY 시나리오 이해

## 데모 시나리오

정책 제어가 있는 **보험 인수 처리 시스템**을 구축합니다:

- **Tool**: 
  - **ApplicationTool** - 지리적 및 자격 검증을 통해 보험 신청서 생성
    - 파라미터: `applicant_region` (string), `coverage_amount` (integer)
  - **RiskModelTool** - 거버넌스 제어를 통해 외부 위험 점수 모델 호출
    - 파라미터: `API_classification` (string), `data_governance_approval` (boolean)
  - **ApprovalTool** - 고액 또는 고위험 인수 결정 승인
    - 파라미터: `claim_amount` (integer), `risk_level` (string)

- **정책 규칙**: $1M 미만의 보장 금액을 가진 보험 신청만 허용
- **테스트 케이스**: 
  - ✅ $750K 신청 (허용됨)
  - ❌ $1.5M 신청 (거부됨)

> **중요**: 정책은 Gateway 대상 스키마에 정의된 파라미터만 참조할 수 있습니다. 각 tool에는 정책 조건에서 사용할 수 있는 특정 파라미터가 있는 자체 스키마가 있습니다.

## 사전 요구 사항

시작하기 전에 다음을 확인하세요:

- 적절한 자격 증명으로 구성된 AWS CLI
- boto3 1.42.0+가 설치된 Python 3.10+
- `bedrock_agentcore_starter_toolkit` 패키지 설치
- `strands` 패키지 설치 (AI agent 기능용)
- AWS Lambda 액세스 (대상 함수 생성용)
- Amazon Bedrock 액세스 (AI agent model용)
- **us-east-1 (N.Virginia)** 리전에서 작업

> **참고**: gateway 설정 스크립트는 AgentCore 서비스에 대한 적절한 신뢰 정책이 있는 필요한 IAM 역할을 자동으로 생성합니다.

## 설정 지침

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

**중요**: boto3 버전 1.42.0 이상이 설치되어 있는지 확인하세요:

```bash
pip install --upgrade boto3
```

### 2. 데모 노트북 열기

```bash
jupyter notebook AgentCore-Policy-Demo.ipynb
```

### 3. 노트북 따라하기

노트북은 다음을 안내합니다:

1. **환경 설정** - 자격 증명 및 의존성 확인
2. **Lambda 배포** - 3개의 Lambda 함수 배포 (ApplicationTool, RiskModelTool, ApprovalTool)
3. **Gateway 설정** - OAuth로 AgentCore Gateway 구성 및 Lambda 대상 연결
4. **Agent 테스트** - 모든 tool에 액세스할 수 있는 AI agent 테스트 (아직 정책 없음)
5. **Policy Engine** - policy engine 생성 및 gateway에 연결
6. **Cedar 정책** - 액세스 제어를 위한 Cedar 정책 작성 및 배포
7. **정책 테스트** - 실제 AI agent 요청으로 ALLOW 및 DENY 시나리오 테스트
8. **정리** - 생성된 모든 리소스 제거

> **참고**: 이 데모는 boto3의 네이티브 policy-registry 클라이언트(boto3 1.42.0+에서 사용 가능)와 AI agent 기능을 위한 Strands 프레임워크를 사용합니다.

## 프로젝트 구조

```
Getting-Started/
├── AgentCore-Policy-Demo.ipynb    # 메인 데모 노트북
├── README.md                       # 이 파일
├── requirements.txt                # Python 의존성
├── config.json                     # 생성된 구성 파일
└── scripts/                        # 지원 스크립트
    ├── setup_gateway.py            # 자동 IAM 역할 생성을 통한 Gateway 설정
    ├── agent_with_tools.py         # AI agent 세션 관리자
    ├── get_client_secret.py        # Cognito 클라이언트 시크릿 검색
    ├── policy_generator.py         # 자연어에서 Cedar로 생성
    └── lambda-target-setup/        # Lambda 배포 스크립트
        ├── deploy_lambdas.py       # 3개의 Lambda 함수 모두 배포
        ├── application_tool.js     # ApplicationTool Lambda 코드
        ├── risk_model_tool.js      # RiskModelTool Lambda 코드
        └── approval_tool.js        # ApprovalTool Lambda 코드
```

## 주요 개념

### AgentCore Gateway

agent가 tool에 액세스할 수 있도록 하는 MCP와 유사한 클라이언트입니다.

### Policy Engine

실시간으로 정의된 규칙에 대해 요청을 평가하는 Cedar 정책 모음입니다.

### Cedar Policy Language

다음 구조를 가진 선언적 정책 언어입니다:

```cedar
permit(
  principal,              // 누가 액세스할 수 있는지 (주체)
  action,                 // 어떤 작업을 수행할 수 있는지 (동작)
  resource                // 어떤 리소스에 액세스할 수 있는지 (대상)
) when {
  conditions              // 어떤 조건에서 (조건절)
};
```

### 정책 모드

- **LOG_ONLY**: 정책을 평가하지만 요청을 차단하지 않음 (테스트용)
- **ENFORCE**: 정책을 위반하는 요청을 적극적으로 차단 (프로덕션용)

## 정책 예시

```cedar
permit(
  principal,
  action == AgentCore::Action::"ApplicationToolTarget___create_application",  // ApplicationTool의 create_application 액션
  resource == AgentCore::Gateway::"<gateway-arn>"  // Gateway ARN 지정
) when {
  context.input.coverage_amount <= 1000000  // 보장 금액이 100만 이하일 때만 허용
};
```

이 정책은:
- $1M 미만의 보장 금액으로 보험 신청 생성 허용
- $1M 이상의 보장 금액으로 신청 거부
- ApplicationTool 대상에 적용
- 실시간으로 `coverage_amount` 파라미터 평가

> **핵심 인사이트**: Policy Engine이 ENFORCE 모드에서 Gateway에 연결되면 기본 작업은 DENY입니다. 액세스를 허용하려는 각 tool에 대해 명시적으로 허용 정책을 생성해야 합니다.

## 아키텍처

```
┌─────────────┐
│   AI Agent  │
└──────┬──────┘
       │ Tool Call Request
       ▼
┌─────────────────────┐
│  AgentCore Gateway  │
│  + OAuth Auth       │
└──────┬──────────────┘
       │ Policy Check
       ▼
┌─────────────────────┐
│   Policy Engine     │
│   (Cedar Policies)  │
└──────┬──────────────┘
       │ ALLOW / DENY
       ▼
┌─────────────────────┐
│   Lambda Target     │
│   (RefundTool)      │
└─────────────────────┘
```

## 테스트

데모에는 실제 AI agent를 사용한 포괄적인 테스트가 포함되어 있습니다:

### Policy Engine 연결 전
- Agent가 3개의 tool을 모두 나열할 수 있음
- Agent가 제한 없이 모든 tool을 호출할 수 있음
- 정책 적용 없음

### Policy Engine 연결 후 (비어 있음)
- Agent가 어떤 tool도 나열할 수 없음 (기본 DENY)
- Agent가 어떤 tool도 호출할 수 없음
- 모든 요청 차단됨

### Application 정책 추가 후
- Agent가 ApplicationTool만 나열할 수 있음
- Agent가 $1M 미만의 신청을 생성할 수 있음 ✅
- Agent가 $1M 이상의 신청을 생성할 수 없음 ❌
- 다른 tool은 차단된 상태로 유지

### 테스트 1: ALLOW 시나리오 ✅
- 요청: $750K 보장 금액으로 신청 생성
- 예상: 허용됨
- 이유: $750K <= $1M
- 결과: Lambda 실행, 신청 생성됨

### 테스트 2: DENY 시나리오 ❌
- 요청: $1.5M 보장 금액으로 신청 생성
- 예상: 거부됨
- 이유: $1.5M > $1M
- 결과: 정책이 요청을 차단, Lambda가 실행되지 않음

## 고급 기능

### 다중 조건

```cedar
permit(...) when {
  context.input.coverage_amount <= 1000000 &&  // 보장 금액 체크
  has(context.input.applicant_region) &&  // applicant_region 필드 존재 여부 확인
  context.input.applicant_region == "US"  // 미국 지역만 허용
};
```

### 리전 기반 조건

```cedar
permit(...) when {
  context.input.applicant_region in ["US", "CA", "UK"]  // 허용된 국가 목록에 포함되는지 확인
};
```

### Risk Model 거버넌스

```cedar
permit(
  principal,
  action == AgentCore::Action::"RiskModelToolTarget___invoke_risk_model",
  resource == AgentCore::Gateway::"<gateway-arn>"
) when {
  context.input.API_classification == "public" &&  // public API만 허용
  context.input.data_governance_approval == true  // 데이터 거버넌스 승인 필수
};
```

### 승인 임계값

```cedar
permit(
  principal,
  action == AgentCore::Action::"ApprovalToolTarget___approve_underwriting",
  resource == AgentCore::Gateway::"<gateway-arn>"
) when {
  context.input.claim_amount <= 100000 &&  // 청구 금액이 10만 이하
  context.input.risk_level in ["low", "medium"]  // 위험 수준이 낮음 또는 중간일 때만
};
```

### 거부 정책

```cedar
forbid(...) when {
  context.input.coverage_amount > 10000000  // 1천만 초과 보장 금액은 명시적으로 거부
};
```

## 모니터링 및 디버깅

### CloudWatch Logs

정책 결정은 CloudWatch에 기록됩니다:

- **Gateway Logs**: 요청/응답 세부 정보
- **Policy Engine Logs**: 정책 평가 결과
- **Lambda Logs**: Tool 실행 세부 정보

### 일반적인 문제

1. **정책이 적용되지 않음**
   - ENFORCE 모드 확인 (LOG_ONLY가 아님)
   - 정책 상태가 ACTIVE인지 확인
   - gateway 연결 확인

2. **모든 요청이 거부됨**
   - 정책 조건 검토
   - 작업 이름이 대상과 일치하는지 확인
   - 리소스 ARN이 gateway와 일치하는지 확인

3. **인증 실패**
   - OAuth 자격 증명 확인
   - 토큰 엔드포인트 접근성 확인
   - client_id 및 client_secret이 올바른지 확인

4. **모듈 가져오기 오류**
   - boto3 1.42.0+가 설치되어 있는지 확인: `pip install --upgrade boto3`
   - strands가 설치되어 있는지 확인: `pip install strands`
   - 의존성 업데이트 후 Jupyter 커널 재시작
   - Python 캐시 지우기: `rm -rf scripts/__pycache__`

5. **Agent 세션 오류**
   - `MCPClientInitializationError`가 표시되면 노트북 커널 재시작
   - config.json에 client_secret 필드가 채워져 있는지 확인
   - 누락된 경우 `scripts/get_client_secret.py`를 실행하여 시크릿 검색

6. **AWS 토큰 만료**
   - AWS 자격 증명 새로 고침: `aws sso login` 또는 `aws configure`
   - 새 자격 증명을 가져오기 위해 노트북 커널 재시작
   - 처음부터 셀 다시 실행


## 추가 리소스

- **Cedar Policy Language**: [Cedar Documentation](https://docs.cedarpolicy.com/)
- **Amazon Bedrock AgentCore Policy**: [AWS AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html)

---

**즐거운 빌딩 되세요!** 🚀
