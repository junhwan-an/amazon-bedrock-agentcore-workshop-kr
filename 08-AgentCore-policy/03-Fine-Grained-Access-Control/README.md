# Amazon Bedrock AgentCore를 위한 Policy

## 개요

Amazon Bedrock AgentCore를 위한 Policy는 Cedar policy를 사용하여 AI agent에 대한 세밀한 접근 제어를 가능하게 합니다. JWT 토큰 클레임을 평가하여 tool 호출을 허용할지 거부할지 결정합니다.

### 아키텍처

```
                                ┌───────────────────────┐
                                │  Policy for AgentCore │
                                │  (Cedar Policies)     │
                                │                       │
                                │  Evaluates:           │
                                │  - principal tags     │
                                │  - context.input      │
                                │  - resource           │
                                └───────────┬───────────┘
                                            │ attached
                                            ▼
┌─────────────────┐             ┌───────────────────────┐             ┌─────────────┐
│   Amazon        │  JWT Token  │  Amazon Bedrock       │             │   Lambda    │
│   Cognito       │────────────▶│  AgentCore Gateway    │────────────▶│   Target    │
│   + AWS Lambda  │  with       │                       │  if ALLOWED │   (Tool)    │
└─────────────────┘  claims     └───────────────────────┘             └─────────────┘
```

### Tutorial 세부 정보

| 정보                  | 세부 사항                                                |
|:---------------------|:--------------------------------------------------------|
| AgentCore 구성 요소   | Gateway, Identity, Policy                               |
| 예제 복잡도           | 중급                                                     |
| 사용된 SDK           | boto3, requests                                         |

## 사전 요구 사항

- 적절한 IAM 권한이 있는 AWS 계정
- OAuth authorizer가 있는 Amazon Bedrock AgentCore Gateway
- Amazon Cognito User Pool (M2M 클라이언트, **Essentials** 또는 **Plus** 티어)
- Python 3.8+

## 시작하기

### 옵션 1: Setup Script (새 리소스)

```bash
# AgentCore 설정을 위한 toolkit 설치
pip install bedrock-agentcore-starter-toolkit
# Gateway 및 관련 리소스 자동 생성
python setup-gateway.py
```

### 옵션 2: 기존 리소스

Gateway 및 Cognito 세부 정보가 포함된 `gateway_config.json`을 생성합니다 (템플릿은 노트북 참조).

### Tutorial 실행

[policy_for_agentcore_tutorial.ipynb](policy_for_agentcore_tutorial.ipynb)를 엽니다

## Cedar Policy 구문

| 패턴 | Cedar 구문 |
|---------|-------------|
| 클레임 존재 확인 | `principal.hasTag("claim_name")` |
| 정확히 일치 | `principal.getTag("claim_name") == "value"` |
| 패턴 일치 | `principal.getTag("claim_name") like "*value*"` |
| 입력 검증 | `context.input.field <= value` |

## 테스트 시나리오

1. **부서 기반** - 특정 부서의 사용자만 허용
2. **그룹 기반** - 특정 그룹의 사용자 허용 (패턴 매칭)
3. **Principal ID 기반** - 특정 클라이언트 애플리케이션 허용
4. **결합 조건** - 입력 검증이 포함된 여러 조건

## 모범 사례

- 오류를 방지하기 위해 `getTag()` 전에 `hasTag()`를 사용하세요
- 패턴 매칭을 신중하게 사용하세요 - `like "*value*"`는 의도하지 않은 문자열과 일치할 수 있습니다
- ALLOW 및 DENY 시나리오를 모두 테스트하세요
- M2M 클라이언트 자격 증명 플로우에는 V3_0 Lambda 트리거를 사용하세요
