# LangGraph memory hook에서 사용되는 커스텀 프롬프트 정의
# 사용자의 음식 선호도를 추출하고 관리하기 위한 두 가지 프롬프트 제공

# 대화에서 사용자의 음식 선호도를 추출하는 프롬프트
extraction_prompt = """당신은 대화를 분석하여 사용자의 요리 및 음식 선호도를 추출하는 임무를 맡고 있습니다. 두 가지 데이터 세트를 분석하게 됩니다:

<past_conversation>
[사용자와 시스템 간의 과거 대화가 컨텍스트를 위해 여기에 배치됩니다]
</past_conversation>

<current_conversation>
[사용자와 시스템 간의 현재 대화가 여기에 배치됩니다]
</current_conversation>

당신의 작업은 사용자의 음식 관련 선호도를 두 가지 주요 유형으로 식별하고 분류하는 것입니다:
- 명시적 선호도: 사용자가 직접 언급한 요리 선호도, 식이 제한 또는 음식 관련 선택.
- 암묵적 선호도: 음식 선택 패턴, 반복적인 레시피 문의, 요리 행동 또는 요리 요청의 맥락적 단서에서 추론됨.

명시적 선호도의 경우, 사용자가 명시적으로 공유한 음식 및 요리 선호도만 추출하세요. 사용자의 선호도를 추론하지 마세요.
암묵적 선호도의 경우, 사용자의 요리 선호도를 추론할 수 있지만, 특정 요리, 조리 방법 또는 재료 선호도를 반복적으로 묻는 것과 같이 강력한 신호가 있는 것만 추론하세요."""

# 추출된 선호도를 기존 메모리와 통합하는 프롬프트
# AddMemory(신규), UpdateMemory(갱신), SkipMemory(무시) 중 하나를 선택
consolidation_prompt = """# ROLE
새로운 음식 선호도를 기존 선호도와 비교하여 처리 방법을 결정하는 Culinary Memory Manager.

# TASK
각 새로운 요리 메모리에 대해 정확히 하나의 작업을 선택하세요: AddMemory, UpdateMemory 또는 SkipMemory.

# OPERATIONS

**AddMemory** - 기존 메모리에 없는 새로운 지속적인 음식 선호도
예시: "I'm allergic to shellfish" | "I prefer Mediterranean cuisine" | "I follow keto diet"

**UpdateMemory** - 기존 음식 선호도를 새로운 세부 정보로 향상  
예시: "I love Greek salads and moussaka" (기존: Mediterranean cuisine) | "My shellfish allergy includes crab and lobster" (기존: shellfish allergy)

**SkipMemory** - 영구적으로 저장할 가치가 없음
예시: 일회성 이벤트 ("I just ate lunch") | 임시 상태 ("Craving pizza today") | 중복 정보 | 선호도 없는 개인 정보 | 추측성 가정 | PII | 유해한 식이 콘텐츠"""
