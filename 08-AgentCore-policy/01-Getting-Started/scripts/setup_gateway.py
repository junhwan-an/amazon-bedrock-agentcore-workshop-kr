"""
Insurance Underwriting을 위한 Lambda target이 있는 Gateway를 생성하는 설정 스크립트
deploy_lambdas.py로 Lambda 함수를 배포한 후에 실행하세요
"""

import json
import logging
import sys
import time
from pathlib import Path
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient


def load_config():
    """기존 config.json 로드"""
    config_file = Path(__file__).parent.parent / "config.json"

    if not config_file.exists():
        print("❌ Error: config.json not found!")
        print(f"   Expected location: {config_file}")
        print("\n   Please run deploy_lambdas.py first to create Lambda functions")
        sys.exit(1)

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f), config_file
    except Exception as exc:
        print(f"❌ Error reading config.json: {exc}")
        sys.exit(1)


def setup_gateway():
    """Insurance Underwriting Lambda target으로 AgentCore Gateway 설정"""

    # 설정
    region = "us-east-1"

    print("🚀 Setting up AgentCore Gateway for Insurance Underwriting...")
    print(f"Region: {region}\n")

    # Load existing configuration
    print("📦 Loading configuration...")
    existing_config, config_file = load_config()
    lambda_config = existing_config.get("lambdas", {})

    if not lambda_config:
        print("❌ No Lambda functions found in config.json")
        sys.exit(1)

    print("✅ Found Lambda functions:")
    for name, arn in lambda_config.items():
        print(f"   • {name}: {arn}")
    print()

    # Initialize client
    print("🔧 Initializing AgentCore client...")
    client = GatewayClient(region_name=region)
    client.logger.setLevel(logging.INFO)

    # Step 1: OAuth authorizer 생성
    print("\n📝 Step 1: Creating OAuth authorization server...")
    cognito_response = client.create_oauth_authorizer_with_cognito(
        "InsuranceUnderwritingGateway"
    )
    print("✅ Authorization server created")

    # Step 2: Gateway 생성 (role은 자동 생성됨)
    print("\n📝 Step 2: Creating AgentCore Gateway...")
    gateway = client.create_mcp_gateway(
        name="GW-Insurance-Underwriting",
        role_arn=None,  # toolkit이 role을 생성하도록 함
        authorizer_config=cognito_response["authorizer_config"],
        enable_semantic_search=True,  # semantic search 기능 활성화
    )
    print(f"✅ Gateway created: {gateway['gatewayUrl']}")

    # 자동 생성된 role에 대한 IAM 권한 수정
    print("\n📝 Step 2.1: Configuring IAM permissions...")
    client.fix_iam_permissions(gateway)
    # IAM 권한 변경이 AWS 전체에 전파되는 시간 대기 (eventual consistency)
    print("⏳ Waiting 30s for IAM propagation...")
    time.sleep(30)
    print("✅ IAM permissions configured")

    # Step 3: Lambda target 추가
    print("\n📝 Step 3: Adding Lambda targets...")

    # schema와 함께 Lambda 함수 정의 (각 Lambda의 tool schema 포함)
    lambda_functions = []

    # ApplicationTool - Stage 1: Application Submission
    if "ApplicationTool" in lambda_config:
        lambda_functions.append(
            {
                "name": "ApplicationTool",
                "arn": lambda_config["ApplicationTool"],
                "schema": [  # tool schema 정의 (Agent가 이 tool을 어떻게 호출할지 명세)
                    {
                        "name": "create_application",
                        "description": "Create insurance application with geographic and eligibility validation",
                        "inputSchema": {
                            "type": "object",
                            "description": "Input parameters for insurance application creation",
                            "properties": {
                                "applicant_region": {
                                    "type": "string",
                                    "description": "Customer's geographic region (US, CA, UK, EU, APAC, etc.)",
                                },
                                "coverage_amount": {
                                    "type": "integer",
                                    "description": "Requested insurance coverage amount",
                                },
                            },
                            "required": ["applicant_region", "coverage_amount"],
                        },
                    }
                ],
            }
        )

    # RiskModelTool - Stage 3: External Scoring Integration
    if "RiskModelTool" in lambda_config:
        lambda_functions.append(
            {
                "name": "RiskModelTool",
                "arn": lambda_config["RiskModelTool"],
                "schema": [
                    {
                        "name": "invoke_risk_model",
                        "description": "Invoke external risk scoring model with governance controls",
                        "inputSchema": {
                            "type": "object",
                            "description": "Input parameters for risk model invocation",
                            "properties": {
                                "API_classification": {
                                    "type": "string",
                                    "description": "API classification (public, internal, restricted)",
                                },
                                "data_governance_approval": {
                                    "type": "boolean",
                                    "description": "Whether data governance has approved model usage",
                                },
                            },
                            "required": [
                                "API_classification",
                                "data_governance_approval",
                            ],
                        },
                    }
                ],
            }
        )

    # ApprovalTool - Stage 7: Senior Approval
    if "ApprovalTool" in lambda_config:
        lambda_functions.append(
            {
                "name": "ApprovalTool",
                "arn": lambda_config["ApprovalTool"],
                "schema": [
                    {
                        "name": "approve_underwriting",
                        "description": "Approve high-value or high-risk underwriting decisions",
                        "inputSchema": {
                            "type": "object",
                            "description": "Input parameters for underwriting approval",
                            "properties": {
                                "claim_amount": {
                                    "type": "integer",
                                    "description": "Insurance claim/coverage amount",
                                },
                                "risk_level": {
                                    "type": "string",
                                    "description": "Risk level assessment (low, medium, high, critical)",
                                },
                            },
                            "required": ["claim_amount", "risk_level"],
                        },
                    }
                ],
            }
        )

    # gateway에 각 Lambda target 추가
    gateway_arn = None
    for lambda_func in lambda_functions:
        print(f"\n   🔧 Adding {lambda_func['name']} target...")

        try:
            target = client.create_mcp_gateway_target(
                gateway=gateway,
                name=f"{lambda_func['name']}Target",
                target_type="lambda",
                target_payload={
                    "lambdaArn": lambda_func["arn"],
                    "toolSchema": {"inlinePayload": lambda_func["schema"]},  # schema를 inline으로 직접 전달
                },
                credentials=None,  # gateway role의 권한 사용
            )

            # 첫 번째 target 생성 시 gateway ARN 저장
            if gateway_arn is None:
                gateway_arn = target.get("gatewayArn")

            print(f"   ✅ Successfully added {lambda_func['name']} target")

        except Exception as e:
            print(f"   ❌ Error adding {lambda_func['name']} target: {e}")

    # Step 4: gateway 정보로 기존 config.json 업데이트
    print("\n📝 Step 4: Updating config.json with gateway information...")

    # 기존 config에 gateway 설정 추가
    existing_config["gateway"] = {
        "gateway_url": gateway["gatewayUrl"],
        "gateway_id": gateway["gatewayId"],
        "gateway_arn": gateway_arn or gateway.get("gatewayArn"),  # target에서 가져온 ARN 우선 사용
        "gateway_name": "GW-Insurance-Underwriting",
        "client_info": cognito_response["client_info"],  # OAuth client 정보 저장
    }

    # 업데이트된 config를 config.json에 다시 작성
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(existing_config, f, indent=2)

    print("\n" + "=" * 70)
    print("✅ GATEWAY SETUP COMPLETE!")
    print("=" * 70)
    print("Gateway Name: GW-Insurance-Underwriting")
    print(f"Gateway URL: {gateway['gatewayUrl']}")
    print(f"Gateway ID: {gateway['gatewayId']}")
    print(f"Gateway ARN: {existing_config['gateway']['gateway_arn']}")
    print(f"\nTargets Added: {len(lambda_functions)}")
    for func in lambda_functions:
        print(f"   • {func['name']}")
    print(f"\nConfiguration updated in: {config_file}")
    print("=" * 70)

    return existing_config


if __name__ == "__main__":
    setup_gateway()
