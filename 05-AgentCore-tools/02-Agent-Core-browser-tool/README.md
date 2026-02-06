# Amazon Bedrock AgentCore Browser Tool

## 개요

Amazon Bedrock AgentCore Browser Tool은 AI agent가 사람처럼 웹사이트와 상호작용할 수 있는 안전하고 완전 관리형 방법을 제공합니다. Agent가 웹 페이지를 탐색하고, 양식을 작성하며, 개발자가 커스텀 자동화 스크립트를 작성하고 유지 관리할 필요 없이 복잡한 작업을 완료할 수 있도록 합니다.

## 작동 방식

Browser tool 샌드박스는 AI agent가 웹 브라우저와 안전하게 상호작용할 수 있도록 하는 보안 실행 환경입니다. 사용자가 요청을 하면 Large Language Model (LLM)이 적절한 tool을 선택하고 명령을 변환합니다. 이러한 명령은 헤드리스 브라우저와 호스팅된 라이브러리 서버(Playwright와 같은 도구 사용)를 포함하는 제어된 샌드박스 환경 내에서 실행됩니다. 샌드박스는 웹 상호작용을 제한된 공간 내에 포함시켜 격리 및 보안을 제공하고, 무단 시스템 액세스를 방지합니다. Agent는 스크린샷을 통해 피드백을 받고 시스템 보안을 유지하면서 자동화된 작업을 수행할 수 있습니다. 이 설정은 AI agent를 위한 안전한 웹 자동화를 가능하게 합니다.

![architecture local](images/browser-tool.png)

## 주요 기능

### 안전하고 관리형 웹 상호작용

AI agent에게 사람처럼 웹사이트와 상호작용할 수 있는 안전하고 완전 관리형 방법을 제공하여, 커스텀 자동화 스크립트 없이도 탐색, 양식 작성 및 복잡한 작업 완료를 가능하게 합니다.

### 엔터프라이즈 보안 기능

사용자 세션과 브라우저 세션 간 1:1 매핑을 통한 VM 수준 격리를 제공하여 엔터프라이즈급 보안을 제공합니다. 각 브라우저 세션은 엔터프라이즈 보안 요구사항을 충족하기 위해 격리된 샌드박스 환경에서 실행됩니다.

### Model 독립적 통합

다양한 AI model 및 프레임워크를 지원하면서 interact(), parse(), discover()와 같은 tool을 통해 브라우저 작업에 대한 자연어 추상화를 제공하여 엔터프라이즈 환경에 특히 적합합니다. 이 tool은 모든 라이브러리에서 브라우저 명령을 실행할 수 있으며 Playwright 및 Puppeteer와 같은 다양한 자동화 프레임워크를 지원합니다.

### 통합

Amazon Bedrock AgentCore Browser Tool은 통합 SDK를 통해 다른 Amazon Bedrock AgentCore 기능과 통합됩니다:

- Amazon Bedrock AgentCore Runtime
- Amazon Bedrock AgentCore Identity
- Amazon Bedrock AgentCore Memory
- Amazon Bedrock AgentCore Observability

이 통합은 개발 프로세스를 단순화하고 AI agent를 구축, 배포 및 관리하기 위한 포괄적인 플랫폼을 제공하며, 브라우저 기반 작업을 수행할 수 있는 강력한 기능을 제공하는 것을 목표로 합니다.

### 사용 사례

Amazon Bedrock AgentCore Browser Tool은 다음을 포함한 광범위한 애플리케이션에 적합합니다:

- 웹 탐색 및 상호작용
- 양식 작성을 포함한 워크플로우 자동화

## 튜토리얼 개요

이 튜토리얼은 다양한 프레임워크 및 구성에서 AgentCore Browser Tool 기능을 보여줍니다:

### 시작하기

**Browser Use 예제**
- [Bedrock AgentCore Browser Tool과 Browser Use 시작하기](02-browser-with-browserUse/getting_started-agentcore-browser-tool-with-browser-use.ipynb)
- [Amazon Bedrock AgentCore Browser Tool Live View와 Browser Use](02-browser-with-browserUse/agentcore-browser-tool-live-view-with-browser-use.ipynb)

**Nova Act 예제**
- [Bedrock AgentCore Browser Tool과 Nova Act 시작하기](01-browser-with-NovaAct/01_getting_started-agentcore-browser-tool-with-nova-act.ipynb)
- [Amazon Bedrock AgentCore Browser Tool Live View와 Nova Act](01-browser-with-NovaAct/02_agentcore-browser-tool-live-view-with-nova-act.ipynb)

**Strands 예제**
- [Bedrock AgentCore Browser Tool과 Strands 시작하기](04-browser-with-Strands/01_getting_started-agentcore-browser-tool-with-strands.ipynb)

### 고급 기능

**Observability**
- [Amazon Bedrock AgentCore Browser Tool Observability](03-browser-observability/01_browser_observability.ipynb)

**Live View**
- [Amazon Bedrock AgentCore Browser Tool DCV Live View](05-browser-live-view/01-embed-dcv-live-view-tutorial.ipynb)

**Web Bot 인증**
- [Amazon Bedrock AgentCore Browser Tool Web Bot Auth](06-Web-Bot-Auth-Signing/01_agentcore-browser-tool-with-web-bot-auth.ipynb)

### VPC 통합

**VPC 구성**
- [Private VPC에서 Public Browser 연결하기](07-connecting-public-browser-from-private-vpc/01-connecting-public-browser-from-private-vpc-runtime.ipynb)
- [VPC에서 VPC 기반 Browser와 상호작용하기](08-Interacting-with-vpc-based-browser-from-vpc/01-Interacting-with-vpc-based-browser-from-vpc.ipynb)
