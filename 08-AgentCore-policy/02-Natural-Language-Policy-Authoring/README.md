# AgentCore Policy - 자연어 Policy 작성 (NL2Cedar)

Amazon Bedrock AgentCore Policy의 NL2Cedar 기능을 사용하여 자연어로부터 Cedar policy를 생성하는 실습 데모입니다.

## 🚀 빠른 시작

1. **의존성 설치**: `pip install -r requirements.txt`
2. **노트북 열기**: `jupyter notebook NL-Authoring-Policy.ipynb`
3. **노트북의 단계를 따라 진행**

> **참고**: 이 데모는 Getting-Started 튜토리얼을 기반으로 합니다. 완료하지 않았다면 노트북이 자동으로 필요한 인프라를 설정합니다.

## 개요

이 데모는 자연어로 권한 부여 요구사항을 작성하고 자동으로 Cedar 구문으로 변환하는 방법을 보여줍니다. NL2Cedar 기능은 다음을 지원합니다:

- Cedar 구문 대신 평문 영어로 policy 작성
- 여러 줄의 문장에서 여러 policy 생성
- ID 속성을 가진 principal 기반 policy 생성
- 생성된 policy가 요구사항과 일치하는지 검증

## 학습 내용

- ✅ 자연어 설명으로부터 Cedar policy 생성
- ✅ 간단한 단일 문장 policy 생성
- ✅ 여러 줄의 문장에서 여러 policy 생성
- ✅ ID 속성을 가진 principal 범위 policy 작성
- ✅ 다양한 policy 구성 및 패턴 이해

## 사전 요구사항

시작하기 전에 다음을 확인하세요:

- 적절한 자격 증명으로 구성된 AWS CLI
- boto3 1.42.0+ 이상이 설치된 Python 3.10+
- `bedrock_agentcore_starter_toolkit` 패키지 설치
- AWS Lambda 접근 권한 (대상 함수용)
- **01-Getting-Started** 튜토리얼 완료 (또는 노트북이 자동으로 설정하도록 허용)

## 데모 시나리오

이 데모는 Getting-Started 튜토리얼의 **보험 인수 시스템**을 3개의 Lambda tool과 함께 사용합니다:

1. **ApplicationTool** - 보험 신청서 생성
   - 파라미터: `applicant_region`, `coverage_amount`

2. **RiskModelTool** - 위험 점수 model 호출
   - 파라미터: `API_classification`, `data_governance_approval`

3. **ApprovalTool** - 인수 결정 승인
   - 파라미터: `claim_amount`, `risk_level`

## 자연어 Policy 예제

### 1. 간단한 단일 문장 Policy

**자연어:**
```
Allow all users to invoke the application tool when the coverage amount 
is under 1 million and the application region is US or CAN
```

**생성된 Cedar Policy:**
```cedar
permit(
  principal,
  action == AgentCore::Action::"ApplicationToolTarget___create_application",
  resource == AgentCore::Gateway::"<gateway-arn>"
) when {
  // 보장 금액이 100만 미만이고
  (context.input.coverage_amount < 1000000) && 
  // 신청 지역이 US 또는 CAN인 경우 허용
  ((context.input.applicant_region == "US") || 
   (context.input.applicant_region == "CAN"))
};
```

### 2. 여러 줄 문장

**자연어:**
```
Allow all users to invoke the risk model tool when data governance approval is true.
Block users from calling the application tool unless coverage amount is present.
```

**결과:** **2개의 별도 policy** 생성 - 하나의 permit과 하나의 forbid policy.

### 3. Principal 기반 Policy

**자연어:**
```
Allow principals with username "test-user" to invoke the risk model tool
```

**생성된 Cedar Policy:**
```cedar
permit(
  principal,
  action == AgentCore::Action::"RiskModelToolTarget___invoke_risk_model",
  resource == AgentCore::Gateway::"<gateway-arn>"
) when {
  // principal이 username 태그를 가지고 있고
  (principal.hasTag("username")) && 
  // 그 값이 "test-user"인 경우 허용
  (principal.getTag("username") == "test-user")
};
```

**자연어:**
```
Forbid principals to access the approval tool unless they have 
the scope group:Controller
```

**생성된 Cedar Policy:**
```cedar
forbid(
  principal,
  action == AgentCore::Action::"ApprovalToolTarget",
  resource == AgentCore::Gateway::"<gateway-arn>"
) when {
  // scope 태그가 없거나 "group:Controller"를 포함하지 않으면 거부
  !((principal.hasTag("scope")) && 
    (principal.getTag("scope") like "*group:Controller*"))
};
```

**자연어:**
```
Block principals from using risk model tool and approval tool 
unless the principal has role "senior-adjuster"
```

**생성된 Cedar Policy:**
```cedar
forbid(
  principal,
  // 여러 action을 배열로 지정 가능
  action in [AgentCore::Action::"RiskModelToolTarget",
             AgentCore::Action::"ApprovalToolTarget"],
  resource == AgentCore::Gateway::"<gateway-arn>"
) when {
  // role 태그가 없거나 "senior-adjuster"가 아니면 거부
  !((principal.hasTag("role")) && 
    (principal.getTag("role") == "senior-adjuster"))
};
```

## NL2Cedar 작동 방식

1. **스키마 인식**: Gateway 대상 스키마가 NL2Cedar에 제공되어 foundation model이 tool 이름과 파라미터를 이해하도록 돕습니다

2. **자연어 입력**: 평문 영어로 권한 부여 요구사항을 제공합니다

3. **Cedar 생성**: 시스템이 구문적으로 올바른 Cedar policy를 생성합니다

4. **Policy 생성**: 생성된 policy를 Policy Engine에 직접 생성할 수 있습니다

## 워크플로우

노트북은 다음을 안내합니다:

1. **환경 설정** - 자격 증명 및 의존성 확인
2. **인프라 확인** - 필요시 Gateway 자동 설정 (Getting-Started에서)
3. **Policy Engine 생성** - NL2Cedar policy용 Policy Engine 생성
4. **간단한 Policy 생성** - 자연어로부터 단일 policy 생성
5. **Policy 생성** - Policy Engine에 생성된 policy 생성
6. **여러 줄 생성** - 여러 줄 문장에서 여러 policy 생성
7. **Principal 기반 Policy** - ID 인식 policy 생성
8. **정리** - 생성된 모든 리소스 제거

## 주요 기능

### 자동 인프라 설정

Getting-Started 튜토리얼을 완료하지 않았다면 노트북이 다음을 수행합니다:
- 3개의 Lambda 함수 배포 (ApplicationTool, RiskModelTool, ApprovalTool)
- OAuth 인증을 사용하는 AgentCore Gateway 생성
- 적절한 스키마로 Lambda 대상 구성
- `config.json`에 구성 저장

### 다중 Policy 생성

일관된 구분 기호(쉼표, 마침표, 세미콜론)가 있는 여러 줄 문장을 제공하면 NL2Cedar가 자동으로:
- 개별 policy 문장 감지
- 각 문장에 대해 별도의 Cedar policy 생성
- `generatedPolicies` 배열에 모든 policy 반환

### Principal 범위 지원

ID 기반 policy의 경우 다음을 참조할 수 있습니다:
- **Username**: `principal.getTag("username")`
- **Role**: `principal.getTag("role")`
- **Scope**: `principal.getTag("scope")`
- **Custom Claims**: OAuth 토큰의 모든 속성

> **💡 팁**: 자연어 문장에 정확한 태그 이름을 제공하면 NL2Cedar가 올바른 Cedar policy를 생성하는 데 도움이 됩니다.


## 모범 사례

1. **구체적으로 작성**: tool 이름, 파라미터 및 조건을 명확하게 명시
2. **정확한 파라미터 이름 사용**: Gateway 스키마에 표시된 대로 파라미터 참조
3. **Principal 속성 지정**: ID 기반 policy의 경우 정확한 태그 이름 언급
4. **줄당 하나의 개념**: 여러 줄 생성의 경우 일관된 구분 기호로 별개의 policy 분리
5. **생성된 Policy 테스트**: 배포하기 전에 항상 생성된 Cedar 구문 검토



## 추가 리소스

- **예제 Policy**: [지원되는 Cedar Policy](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/example-policies.html)
- **Getting Started 튜토리얼**: `../01-Getting-Started/README.md`

---

**즐거운 개발 되세요!** 🚀
