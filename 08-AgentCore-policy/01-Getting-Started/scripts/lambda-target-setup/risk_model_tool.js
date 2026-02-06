/**
 * RiskModelTool - 간소화된 위험 Model
 * 위험 점수 model을 호출하고 평가를 반환
 * 
 * Parameters:
 * - API_classification: API 분류 (public, internal, restricted)
 * - data_governance_approval: 데이터 거버넌스가 model 사용을 승인했는지 여부
 */

import crypto from 'crypto';

// 간소화된 위험 model 함수
function invokeRiskModel(args) {
    console.log('Processing risk model invocation:', JSON.stringify(args, null, 2));
    
    const {
        API_classification,
        data_governance_approval
    } = args;
    
    // 필수 매개변수 검증
    if (!API_classification) {
        return {
            status: 'ERROR',
            message: 'API classification is required',
            risk_score: null
        };
    }
    
    // undefined와 null 모두 체크 (false는 유효한 값)
    if (data_governance_approval === undefined || data_governance_approval === null) {
        return {
            status: 'ERROR', 
            message: 'Data governance approval status is required',
            risk_score: null
        };
    }
    
    // 모의 위험 점수 생성 및 간단한 응답 반환
    const riskScore = Math.floor(Math.random() * 100);
    const modelId = `MDL-${crypto.randomBytes(4).toString('hex').toUpperCase()}`; // crypto 모듈로 랜덤 ID 생성
    
    return {
        status: 'SUCCESS',
        message: `Risk assessment complete: applicant scored ${riskScore}/100 with moderate confidence based on credit history, claims frequency, and demographic factors indicating standard underwriting eligibility.`,
        model_id: modelId,
        risk_score: riskScore,
        API_classification: API_classification,
        governance_approved: data_governance_approval,
        executed_at: new Date().toISOString()
    };
}

// AgentCore MCP 프로토콜을 따르는 메인 Lambda 핸들러
export const handler = async (event) => {
    console.log('Received event:', JSON.stringify(event, null, 2));
    
    try {
        let args;
        let isJsonRpc = false;
        
        // JSON-RPC 형식인지 직접 매개변수 형식인지 확인
        // MCP 프로토콜은 JSON-RPC 2.0을 사용하고, API Gateway는 직접 매개변수를 전달
        if (event.method === 'tools/call' && event.params) {
            // JSON-RPC 형식 (MCP 프로토콜)
            isJsonRpc = true;
            const requestId = event.id || 'unknown';
            const params = event.params || {};
            const functionName = params.name;
            args = params.arguments || {};
            
            // 함수 이름 검증
            if (functionName !== 'invoke_risk_model') {
                return {
                    jsonrpc: '2.0',
                    id: requestId,
                    error: {
                        code: -32601, // JSON-RPC 표준 에러 코드: Method not found
                        message: `Function not found: ${functionName}`
                    }
                };
            }
        } else {
            // 직접 매개변수 형식 (API Gateway 직접 호출)
            args = event;
        }
        
        // 함수 실행
        const result = invokeRiskModel(args);
        
        // 적절한 형식으로 응답 반환 (호출 방식에 따라 다른 형식 사용)
        if (isJsonRpc) {
            // JSON-RPC 응답 (MCP 프로토콜 표준)
            const responseText = JSON.stringify(result, null, 2);
            return {
                jsonrpc: '2.0',
                id: event.id,
                result: {
                    content: [
                        {
                            type: 'text',
                            text: responseText
                        }
                    ],
                    isError: result.status === 'ERROR'
                }
            };
        } else {
            // 직접 응답 (API Gateway용)
            return result;
        }
        
    } catch (error) {
        console.error('Handler error:', error);
        
        // 적절한 형식으로 오류 반환 (호출 방식에 따라 다른 형식 사용)
        if (event.method === 'tools/call') {
            // JSON-RPC 에러 응답
            return {
                jsonrpc: '2.0',
                id: event.id || 'unknown',
                error: {
                    code: -32603, // JSON-RPC 표준 에러 코드: Internal error
                    message: `Internal error: ${error.message}`
                }
            };
        } else {
            // 직접 에러 응답
            return {
                status: 'ERROR',
                message: `Internal error: ${error.message}`
            };
        }
    }
};

// 로컬 개발용 테스트 함수
// 로컬에서 테스트하려면 주석 해제: node risk_model_tool.js
/*
const testEvent = {
    jsonrpc: '2.0',
    id: 'test-1',
    method: 'tools/call',
    params: {
        name: 'invoke_risk_model',
        arguments: {
            API_classification: 'internal',
            data_governance_approval: true
        }
    }
};

handler(testEvent).then(result => {
    console.log('Test result:', JSON.stringify(result, null, 2));
});
*/
