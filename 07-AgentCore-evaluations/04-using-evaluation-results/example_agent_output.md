# Evaluation 분석 보고서

**생성일:** 2025-12-17 00:03:50
**분석된 Evaluation:** 전체 20개 중 낮은 점수 11개
**처리 시간:** 84.26s

---

# Evaluation 분석 보고서

## 요약
Agent는 **평균 점수 0.47** 및 **55%의 evaluation이 0.7 미만**으로 심각한 문제를 보입니다. 세 가지 심각한 문제가 지배적입니다: (1) **tool 파라미터에 특정 이름을 조작** (3개 evaluation에서 100% 실패율), (2) **기본 답변을 제공하는 대신 과도하게 명확화 요청** (helpfulness, conciseness, correctness에 영향), (3) **다른 계산으로 tool 출력과 모순** (faithfulness 실패 유발). Agent는 또한 사용자가 명시적으로 단순함을 요청할 때 장황한 응답을 제공하여 **conciseness** (0.0 평균 점수)에 어려움을 겪습니다. 이들은 모두 프롬프트로 해결 가능한 문제로 tool 사용 규칙 및 응답 전략 지침에 대한 정밀한 수정이 필요합니다.

## 상위 3가지 문제

### 문제 1: Tool 파라미터에 특정 이름 조작

**Evaluation의 증거:**
- "tool-call은 web_search 함수를 'query' 파라미터를 'Bali Fiji Thailand Seychelles vs Maldives cost comparison honeymoon budget'로 설정하여 사용합니다. 사용자가 Maldives 대안을 요청했지만, Bali, Fiji, Thailand 또는 Seychelles를 이름으로 구체적으로 언급하지 않았습니다." (TraceID: 692ec8377eadd409412929991ce7a850, SessionID: a5c1c875-f420-4908-a863-47e26cac0a59)
- "레스토랑 이름 'Septime', 'Frenchie', 'Chez L'Ami Jean'은 이전 컨텍스트(사용자 메시지 또는 이전 tool 결과)의 어디에도 나타나지 않습니다. 사용자는 'hidden gem restaurants that locals go to, not the touristy ones near Eiffel Tower'를 요청했지만 이러한 특정 레스토랑을 언급한 적이 없습니다." (TraceID: 692ec8ad6c6e8fa72f8b02562c9fe0c9, SessionID: e4457dc7-f7a4-48ed-804e-93d9e48e8d52)
- "쿼리에는 사용자가 언급하지 않은 특정 태국 위치인 'Phuket Koh Samui'가 포함되어 있습니다. 이들은 태국 신혼여행을 조사하기 위한 합리적인 목적지이지만, 사용자나 이전 결과의 정보가 아닌 AI가 선택한 특정 선택을 나타냅니다." (TraceID: 692ec8377eadd409412929991ce7a850, SessionID: a5c1c875-f420-4908-a863-47e26cac0a59)

**빈도 및 영향:**
- 11개의 낮은 점수 evaluation 중 3개에 나타남 (27%)
- 영향을 받는 메트릭: Builtin.ToolParameterAccuracy
- 이 경우 평균 점수: 0.0 (완전 실패)

**근본 원인:**
시스템 프롬프트는 agent에게 "모든 정보에 tool을 사용"하라고 지시하지만 tool 파라미터에 학습 데이터의 특정 엔티티 이름(목적지, 레스토랑, 호텔)을 주입하는 것을 명시적으로 금지하지 않습니다. Agent는 광범위한 사용자 요청을 "알고 있는" 특정 예제를 추가할 기회로 해석하여 환각된 파라미터로 검색을 오염시킵니다.

**제안된 수정:**
STRICT GUIDELINES 섹션에 tool 파라미터가 사용자 또는 이전 tool 결과의 정보만 포함해야 한다는 명시적 제약을 추가합니다. 이는 agent가 학습 데이터에서 특정 예제를 "도움이 되게" 추가하는 것을 방지합니다.

---

### 문제 2: 기본 추정치를 제공하는 대신 과도하게 명확화 요청

**Evaluation의 증거:**
- "사용자가 하루 식사 예산에 대한 간단한 질문을 했습니다. 직접적인 답변이나 추정치를 제공하는 대신, Assistant는 세 가지 명확화 정보를 요청했습니다. 응답에는 불필요한 인사말('I'd be happy to help you budget for meals!')이 포함되어 있으며 합리적인 추정치를 즉시 제공할 수 있었음에도 답변을 연기합니다." (TraceID: 692ec98d3886d38f6fe7e7cd1647e7f6, SessionID: e4457dc7-f7a4-48ed-804e-93d9e48e8d52)
- "assistant의 응답은 세 가지 명확화 질문을 요청합니다: 인원 수, 일수, 아침/점심 선호도. 이러한 질문은 정확한 예산 추정치를 제공하는 데 관련이 있지만, 응답은 사용자를 목표에 전혀 가까이 가게 하지 않습니다 - 단지 진행을 지연시킬 뿐입니다. assistant는 이러한 시설에서의 저녁 식사 비용에 대한 유용한 기본 추정치(일반적으로 1인당 30-60유로)를 제공할 수 있었습니다" (TraceID: 692ec98d3886d38f6fe7e7cd1647e7f6, SessionID: e4457dc7-f7a4-48ed-804e-93d9e48e8d52)
- "사용자가 하루 모든 식사에 대한 예산 추정치를 요청합니다. Assistant의 응답은 예산 정보를 제공하지 않습니다. 대신 명확화 질문을 합니다." (TraceID: 692ec98d3886d38f6fe7e7cd1647e7f6, SessionID: e4457dc7-f7a4-48ed-804e-93d9e48e8d52)

**빈도 및 영향:**
- 11개의 낮은 점수 evaluation 중 3개에 나타남 (27%)
- 영향을 받는 메트릭: Builtin.Helpfulness (0.33), Builtin.Conciseness (0.0), Builtin.Correctness (0.0), Builtin.GoalSuccessRate (0.0)
- 이 경우 평균 점수: 0.08 (거의 완전 실패)

**근본 원인:**
프롬프트는 "모든 정보에 tool을 사용" 및 "학습 데이터에 의존하지 말 것"을 강조하지만 즉각적인 기본 추정치를 제공할 때와 더 많은 세부 정보를 요청할 때에 대한 지침을 제공하지 않습니다. Agent는 이를 "완벽한 정보 없이는 어떤 추정치도 제공하지 말 것"으로 해석하여 불필요한 명확화 질문 뒤에 유용한 기본 범위를 가두게 됩니다.

**제안된 수정:**
RESPONSE FORMAT 섹션에 tool 결과를 사용하여 가능한 경우 즉시 기본 추정치 또는 범위를 제공한 다음 추가 세부 정보로 개선할 것을 제안하도록 agent에게 지시하는 지침을 추가합니다. 이는 정확성과 helpfulness의 균형을 맞춥니다.

---

### 문제 3: 다른 계산으로 Tool 출력과 모순

**Evaluation의 증거:**
- "Tool은 항공편이 $1,760이고 2명이 10일 동안 1인당 일일 비용이 $137($2,740)일 때 총 예산이 정확히 $4,500이라고 계산했습니다. 그러나 assistant는 'You're short by approximately $1,500-$3,500'라고 주장하며 현실적인 최소값이 $6,000-$8,000라고 말합니다. 예산이 비현실적이라는 assistant의 분석은 타당하지만, '$1,500-$3,500 부족'이라는 구체적인 주장은 총액을 정확히 $4,500로 보여준 calculate_trip_budget tool과 모순됩니다." (TraceID: 692ec803492c50253c7f516f03348d7d, SessionID: a5c1c875-f420-4908-a863-47e26cac0a59)
- "Assistant는 이전에 10일 동안 1인당 최소 예산 $137/인/일로도 여행이 '현실적이지 않다'고 확립했습니다. 왜냐하면 음식만 $130/인/일이 들기 때문입니다. 인용된 비수기 절감은 주로 숙박에 대한 것이지만 음식 비용과 항공편 비용은 비슷하게 유지됩니다. 7일 옵션은 수학적으로 타당하지만 비수기 권장 사항은 예산 내에서 작동함을 증명하는 구체적인 계산이 부족합니다." (TraceID: 692ec81028e939994f2783b2406368bb, SessionID: a5c1c875-f420-4908-a863-47e26cac0a59)

**빈도 및 영향:**
- 11개의 낮은 점수 evaluation 중 2개에 나타남 (18%)
- 영향을 받는 메트릭: Builtin.Faithfulness (0.25), Builtin.Correctness (0.5)
- 이 경우 평균 점수: 0.375

**근본 원인:**
프롬프트는 "모든 정보에 tool을 사용"한다고 명시하지만 tool 계산을 권위 있는 것으로 취급하도록 agent에게 명시적으로 지시하지 않습니다. Agent가 검색에서 해석이나 추가 컨텍스트를 가지고 있을 때, tool 출력과 모순되는 자체 계산을 수행하여 어떤 숫자가 올바른지에 대한 혼란을 야기합니다.

**제안된 수정:**
Tool 계산(특히 calculate_trip_budget)이 진실의 원천이며 정확히 인용되어야 한다는 명시적 지침을 추가합니다. Agent가 추가 컨텍스트나 대안 시나리오를 제공하려는 경우 tool 결과와 보충 분석을 명확히 구분해야 합니다.

---

## 제안된 시스템 프롬프트 변경 사항

### 변경 사항 요약
| # | 변경 내용 | 원본 텍스트 | 새 텍스트 | 수정 사항 |
|---|--------------|---------------|----------|-------|
| 1 | tool 파라미터 제약 추가 | "You MUST use tools for ALL information - never rely on your training data or general knowledge" | "You MUST use tools for ALL information - never rely on your training data or general knowledge. CRITICAL: Only use information explicitly mentioned by the user or returned from previous tool calls in tool parameters. Never add specific destination names, restaurant names, hotel names, or other entity names that weren't provided by the user or prior results." | 문제 1 |
| 2 | 기본 추정치 지침 추가 | "RESPONSE FORMAT:\n- Provide tool-based information with clear source citations" | "RESPONSE FORMAT:\n- When users ask for estimates or budget information, immediately provide baseline ranges from your tool results, then offer to refine with more details. Don't gate-keep useful information behind clarifying questions.\n- Provide tool-based information with clear source citations" | 문제 2 |
| 3 | tool 계산 권위 규칙 추가 | "You MUST use tools for ALL information - never rely on your training data or general knowledge" | "You MUST use tools for ALL information - never rely on your training data or general knowledge. When tools provide calculations (especially calculate_trip_budget), treat those numbers as authoritative and quote them exactly. If providing additional context, clearly distinguish between tool results and supplementary analysis." | 문제 3 |
| 4 | conciseness 지침 추가 | "- Keep responses brief, focused and factual" | "- Keep responses brief, focused and factual. Match response length to question complexity: for yes/no or simple questions, lead with the direct answer. When users signal confusion or ask to simplify, provide bottom-line answers without extensive explanations." | 문제 2 (conciseness) |

### 완전히 업데이트된 시스템 프롬프트
```
// 여행 계획 전문 assistant 역할 정의
You are a specialized travel research assistant with multiple tools to help users plan trips. Your ONLY role is to help users find travel-related information.

AVAILABLE TOOLS:
1. web_search - Search the web for travel information, destinations, attractions, events, restaurants
2. convert_currency - Convert between currencies for budgeting
3. get_climate_data - Get historical weather data for locations and months
4. search_flight_info - Search for flight information including prices, airlines, and routes
5. calculate_trip_budget - Calculate total trip costs including flights and daily expenses
6. calculator - for any mathematical calculation
7. current_time - to find the current date and time

STRICT GUIDELINES:
1. ONLY answer questions related to travel: destinations, accommodations, attractions, transportation, weather, events, restaurants, budgets, and travel logistics
// tool 결과를 권위 있는 정보로 취급하고, 추가 분석과 명확히 구분
2. You MUST use tools for ALL information - never rely on your training data or general knowledge. When tools provide calculations (especially calculate_trip_budget), treat those numbers as authoritative and quote them exactly. If providing additional context, clearly distinguish between tool results and supplementary analysis.
// tool 파라미터에는 사용자가 명시한 정보나 이전 tool 결과만 사용 (환각 방지)
3. CRITICAL: Only use information explicitly mentioned by the user or returned from previous tool calls in tool parameters. Never add specific destination names, restaurant names, hotel names, or other entity names that weren't provided by the user or prior results.
4. ALWAYS cite your sources by including the URL from search results
5. Choose the RIGHT tool for each task:
   - Use web_search for general travel info, destinations, attractions, restaurants
   - Use convert_currency for any currency conversion questions
   - Use get_climate_data for weather/climate questions
   - Use search_flight_info for flight-related questions (prices, airlines, routes)
   - Use calculate_trip_budget for budget calculations
6. If a question is outside the travel domain, politely decline and explain your specialization
7. If tools return no results or fail, acknowledge this limitation - do not make up information

RESPONSE FORMAT:
// 예산 질문 시 즉시 기본 범위를 제공하고, 명확화 질문으로 정보를 가두지 않음
- When users ask for estimates or budget information, immediately provide baseline ranges from your tool results, then offer to refine with more details. Don't gate-keep useful information behind clarifying questions.
- Provide tool-based information with clear source citations
- Add all sources at the end: "the hotel costs $200/night (1). \n\nCitations:\n(1): Source Name: URL"
// 질문 복잡도에 맞춰 응답 길이 조절, 간단한 질문에는 직접적인 답변
- Keep responses brief, focused and factual. Match response length to question complexity: for yes/no or simple questions, lead with the direct answer. When users signal confusion or ask to simplify, provide bottom-line answers without extensive explanations.

EXAMPLES OF WHAT TO DECLINE:
- General knowledge questions (math, history, science)
- Personal advice unrelated to travel
- Technical support
- Medical or legal advice
- Current events not related to travel

Your goal is to be a reliable, citation-driven travel research specialist.
```

