# AWS 설정
AWS_REGION = "us-east-1"

# AgentCore 런타임 설정
# TODO: <YOUR_ACCOUNT_ID>와 <YOUR_AGENT_NAME>을 실제 값으로 교체
AGENT_ARN = "arn:aws:bedrock-agentcore:us-east-1:<YOUR_ACCOUNT_ID>:runtime/<YOUR_AGENT_NAME>"
QUALIFIER = "DEFAULT"  # Agent 버전 qualifier
LOG_GROUP_NAME = "/aws/bedrock-agentcore/runtimes/<YOUR_AGENT_NAME>-DEFAULT"
SERVICE_NAME = "<YOUR_AGENT_NAME>.DEFAULT"

# Online Evaluation 설정
EVAL_CONFIG_NAME = "actor_simulator_online_eval"
EVAL_DESCRIPTION = "Online evaluation for actor simulator test cases with builtin metrics"
# TODO: <YOUR_ACCOUNT_ID>를 실제 AWS 계정 ID로 교체
EVALUATION_ROLE_ARN = "arn:aws:iam::<YOUR_ACCOUNT_ID>:role/AgentCoreEvaluationRole"
SAMPLING_PERCENTAGE = 100.0  # 전체 테스트 케이스의 100% 평가
SESSION_TIMEOUT_MINUTES = 5
EVALUATION_ENDPOINT_URL = "https://bedrock-agentcore-control.us-east-1.amazonaws.com"

# Bedrock AgentCore의 내장 평가 지표
EVALUATORS = [
    "Builtin.Helpfulness",  # 응답의 유용성
    "Builtin.ToolSelectionAccuracy",  # 도구 선택 정확도
    "Builtin.Faithfulness",  # 정보의 충실성
    "Builtin.GoalSuccessRate",  # 목표 달성률
    "Builtin.ToolParameterAccuracy",  # 도구 파라미터 정확도
    "Builtin.Correctness"  # 응답 정확성
]

# Agent 능력 정의 (테스트 케이스 생성에 사용)
AGENT_CAPABILITIES = "Simple arithmetic: addition, subtraction, multiplication, division"
AGENT_LIMITATIONS = "Cannot solve trigonometry, calculus, linear algebra, or multi-step word problems"
AGENT_TOOLS = ["calculator"]
AGENT_TOPICS = ["basic mathematics", "simple arithmetic", "number comparison"]
AGENT_COMPLEXITY = "single-step or two-step calculations only"

# Actor Simulator 테스트 생성 설정
NUM_TEST_CASES = 10  # 생성할 테스트 케이스 수
MAX_TURNS = 7  # 대화당 최대 턴 수
