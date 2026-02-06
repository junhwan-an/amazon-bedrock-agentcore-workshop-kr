"""
gateway 호출을 허용하기 위해 Lambda 함수에 리소스 기반 권한 추가
이것은 gateway 호출 문제에 대한 가장 일반적인 해결 방법입니다
"""

import boto3
import json


def add_lambda_permissions():
    """gateway가 Lambda 함수를 호출할 수 있도록 권한 추가"""

    print("🔧 Gateway를 위한 Lambda 권한 추가 중\n")
    print("=" * 70)

    # gateway 설정 로드
    with open("gateway_config.json", "r") as f:
        gateway_config = json.load(f)

    region = gateway_config["region"]
    gateway_arn = gateway_config["gateway_arn"]
    # ARN 형식: arn:aws:service:region:account-id:resource
    # 콜론으로 분리하여 account-id 추출 (인덱스 4)
    gateway_account = gateway_arn.split(":")[4]

    print(f"Gateway ARN: {gateway_arn}\n")

    # Lambda 클라이언트 초기화
    lambda_client = boto3.client("lambda", region_name=region)

    # 업데이트할 Lambda 함수들
    functions = ["ApplicationTool", "RiskModelTool", "ApprovalTool"]

    for function_name in functions:
        print(f"🔧 {function_name}:")

        try:
            # 함수가 존재하는지 확인
            lambda_client.get_function(FunctionName=function_name)

            # 권한 추가 시도
            try:
                lambda_client.add_permission(
                    FunctionName=function_name,
                    StatementId="AllowAgentCoreGateway",  # 권한 정책의 고유 식별자
                    Action="lambda:InvokeFunction",
                    Principal="bedrock-agentcore.amazonaws.com",  # Bedrock AgentCore 서비스가 호출 가능
                    SourceArn=gateway_arn,  # 특정 gateway만 호출 허용 (보안 강화)
                )
                print("   ✅ 권한이 성공적으로 추가되었습니다")

            except lambda_client.exceptions.ResourceConflictException:
                print("   ℹ️  권한이 이미 존재합니다")

                # 제거 후 재추가하여 업데이트 시도 (기존 권한 덮어쓰기 불가하므로)
                try:
                    lambda_client.remove_permission(
                        FunctionName=function_name, StatementId="AllowAgentCoreGateway"
                    )

                    lambda_client.add_permission(
                        FunctionName=function_name,
                        StatementId="AllowAgentCoreGateway",
                        Action="lambda:InvokeFunction",
                        Principal="bedrock-agentcore.amazonaws.com",
                        SourceArn=gateway_arn,
                    )
                    print("   ✅ 권한이 성공적으로 업데이트되었습니다")

                except Exception as update_error:
                    print(f"   ⚠️  권한을 업데이트할 수 없습니다: {update_error}")

        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"   ❌ 계정 {gateway_account}에서 함수를 찾을 수 없습니다")
            print("   → 먼저 Lambda를 배포하세요")

        except Exception as e:
            print(f"   ❌ 오류: {e}")

        print()

    print("=" * 70)
    print("\n✅ 권한 업데이트가 완료되었습니다!")
    print("\n다음 단계:")
    print("1. gateway 호출 테스트")
    print("2. 여전히 실패하는 경우, Lambda 함수의 CloudWatch 로그 확인")
    print("3. gateway IAM role에 lambda:InvokeFunction 권한이 있는지 확인")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    add_lambda_permissions()
