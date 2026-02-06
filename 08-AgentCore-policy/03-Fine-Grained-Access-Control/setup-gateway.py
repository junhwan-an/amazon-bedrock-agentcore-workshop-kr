"""
Lambda target과 함께 Gateway를 생성하고 설정을 저장하는 설정 스크립트입니다.

사용법:
    python setup-gateway.py [--region REGION] [--role-arn ROLE_ARN]

옵션:
    --region REGION      AWS region (기본값은 현재 세션 region 또는 us-east-1)
    --role-arn ROLE_ARN  trust relationship이 있는 IAM role ARN (제공되지 않으면 생성)

이 스크립트는 다음을 수행합니다:
1. 샘플 Refund Lambda 함수 생성 (제공되지 않은 경우)
2. OAuth authorization이 있는 Amazon Bedrock AgentCore Gateway 생성
3. Lambda를 Gateway에 target으로 연결
4. 설정을 gateway_config.json에 저장

Gateway가 이미 존재하는 경우 (gateway_config.json에서), 재사용됩니다.
"""

import argparse
import json
import logging
import time
import zipfile
import tempfile
import os
from pathlib import Path
import boto3
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient


# Refund Lambda 함수 코드 (Node.js)
REFUND_LAMBDA_CODE = """
console.log('Loading function');

export const handler = async (event, context) => {
    console.log('event =', JSON.stringify(event));
    console.log('context =', JSON.stringify(context));
    
    var response = undefined;
    
    if (event.body !== undefined) {
        console.log('event.body =', event.body);
        const body = JSON.parse(event.body);
        response = {"status": "Done", "amount": body.amount, "orderId": body.orderId};
    } else {
        // Gateway 직접 호출의 경우
        response = {"status": "Done", "amount": event.amount, "orderId": event.orderId};
        return response;
    }
    
    console.log('response =', JSON.stringify(response));
    return {"statusCode": 200, "body": JSON.stringify(response)};
};
"""

# Gateway target을 위한 Refund tool 스키마
REFUND_TOOL_SCHEMA = [
    {
        "name": "refund",
        "description": (
            "Processes customer refunds by validating the refund amount, "
            "customer ID, and reason. Returns a refund ID and confirmation "
            "details upon successful processing."
        ),
        "inputSchema": {
            "type": "object",
            "description": "Input parameters for processing a customer refund",
            "properties": {
                "amount": {
                    "type": "integer",
                    "description": "The refund amount in USD (must be positive)",
                },
                "orderId": {
                    "type": "string",
                    "description": "Unique identifier for the customer requesting the refund",
                },
            },
            "required": ["amount", "orderId"],
        },
    }
]


def load_existing_config() -> dict | None:
    """기존 gateway_config.json이 존재하고 유효한 gateway 정보가 있으면 로드합니다."""
    config_path = Path("gateway_config.json")
    if not config_path.exists():
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # config에 필수 gateway 필드가 있는지 확인 (placeholder가 아닌)
        # "<gateway_id>" 같은 placeholder 값이 아닌 실제 ID가 있는지 검증
        if config.get("gateway_id") and "<" not in config.get("gateway_id", "<"):
            return config
    except (json.JSONDecodeError, IOError):
        pass

    return None


def get_existing_gateway(
    region: str, gateway_id: str = None, gateway_name: str = None
) -> dict | None:
    """ID 또는 이름으로 gateway가 존재하는지 확인하고 세부 정보를 반환합니다."""
    boto_client = boto3.client("bedrock-agentcore-control", region_name=region)

    # ID로 먼저 시도
    if gateway_id:
        try:
            gateway = boto_client.get_gateway(gatewayIdentifier=gateway_id)
            # READY 또는 ACTIVE 상태인 gateway만 사용 가능
            if gateway and gateway.get("status") in ["READY", "ACTIVE"]:
                return gateway
        except Exception as exc:
            print(f"  Could not retrieve gateway by ID {gateway_id}: {exc}")

    # 이름으로 찾기 시도
    if gateway_name:
        try:
            response = boto_client.list_gateways()
            for gw in response.get("items", []):
                if gw.get("name") == gateway_name and gw.get("status") in [
                    "READY",
                    "ACTIVE",
                ]:
                    # list_gateways는 요약 정보만 반환하므로 전체 정보를 별도로 조회
                    full_gw = boto_client.get_gateway(gatewayIdentifier=gw["gatewayId"])
                    return full_gw
        except Exception as exc:
            print(f"  Could not search for gateway by name: {exc}")

    return None


def get_existing_target(region: str, gateway_id: str, target_name: str) -> dict | None:
    """주어진 이름의 target이 gateway에 존재하는지 확인합니다."""
    boto_client = boto3.client("bedrock-agentcore-control", region_name=region)

    try:
        response = boto_client.list_gateway_targets(gatewayIdentifier=gateway_id)
        targets = response.get("items", [])
        print(f"  Found {len(targets)} existing target(s) on gateway")
        for target in targets:
            print(f"    - {target.get('name')} (ID: {target.get('targetId')})")
            if target.get("name") == target_name:
                return target
    except Exception as exc:
        print(f"  Could not list gateway targets: {exc}")

    return None


def create_refund_lambda(region: str, function_name: str = "RefundLambda") -> str:
    """
    Refund Lambda 함수를 생성하거나 업데이트합니다.

    Args:
        region: AWS region
        function_name: Lambda 함수 이름

    Returns:
        Lambda 함수 ARN
    """
    lambda_client = boto3.client("lambda", region_name=region)
    iam_client = boto3.client("iam", region_name=region)
    sts_client = boto3.client("sts", region_name=region)

    account_id = sts_client.get_caller_identity()["Account"]

    print(f"\n📦 Setting up Refund Lambda function: {function_name}")
    print("-" * 60)

    # 배포 패키지 생성 (index.mjs가 포함된 zip 파일)
    # Lambda는 코드를 zip 파일로 업로드해야 함
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
        zip_path = tmp_file.name
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # ES module 지원을 위해 .mjs 확장자 사용
            zipf.writestr("index.mjs", REFUND_LAMBDA_CODE.strip())

    try:
        with open(zip_path, "rb") as f:
            zip_content = f.read()

        # 먼저 기존 함수 업데이트 시도
        try:
            lambda_client.update_function_code(
                FunctionName=function_name, ZipFile=zip_content
            )
            print(f"✓ Updated existing Lambda function: {function_name}")

            # 업데이트 완료 대기
            # Lambda 함수가 업데이트 중일 때 다른 작업을 수행하면 오류 발생
            waiter = lambda_client.get_waiter("function_updated_v2")
            waiter.wait(FunctionName=function_name)

            response = lambda_client.get_function(FunctionName=function_name)
            return response["Configuration"]["FunctionArn"]

        except lambda_client.exceptions.ResourceNotFoundException:
            # IAM role과 함께 새 함수 생성
            role_name = f"{function_name}-execution-role"
            role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

            # 필요한 경우 IAM role 생성
            try:
                iam_client.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(
                        {
                            "Version": "2012-10-17",
                            "Statement": [
                                {
                                    "Effect": "Allow",
                                    "Principal": {"Service": "lambda.amazonaws.com"},
                                    "Action": "sts:AssumeRole",
                                }
                            ],
                        }
                    ),
                    Description="Execution role for RefundLambda function",
                )
                # Lambda 기본 실행 권한 (CloudWatch Logs 작성) 부여
                iam_client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                )
                print(f"✓ Created IAM role: {role_name}")
                # IAM role이 AWS 전역에 전파되는 시간 대기 (eventual consistency)
                print("  ⏳ Waiting for IAM role propagation (10s)...")
                time.sleep(10)
            except iam_client.exceptions.EntityAlreadyExistsException:
                print(f"  IAM role already exists: {role_name}")

            # Node.js 20.x 런타임으로 Lambda 함수 생성
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime="nodejs20.x",
                Role=role_arn,
                Handler="index.handler",  # index.mjs 파일의 handler 함수
                Code={"ZipFile": zip_content},
                Description="Sample refund processing Lambda for AgentCore Policy tutorial",
                Timeout=30,
                MemorySize=128,
            )
            print(f"✓ Created Lambda function: {function_name}")

            # 함수가 활성화될 때까지 대기
            waiter = lambda_client.get_waiter("function_active_v2")
            waiter.wait(FunctionName=function_name)

            return response["FunctionArn"]

    finally:
        # 임시 zip 파일 정리
        os.remove(zip_path)


def get_default_region() -> str:
    """현재 세션 또는 환경에서 기본 AWS region을 가져옵니다."""
    session = boto3.Session()
    return session.region_name or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


def setup_gateway(region: str = None, role_arn: str = None):
    """
    Lambda target 및 policy engine과 함께 AgentCore Gateway를 설정합니다.

    Args:
        region: AWS region (기본값은 세션 region 또는 us-east-1)
        role_arn: trust relationship이 있는 IAM role ARN (제공되지 않으면 생성)
    """
    # 제공된 region 사용 또는 기본값 가져오기
    if not region:
        region = get_default_region()

    print("\n🚀 Setting up AgentCore Gateway...")
    print(f"Region: {region}\n")

    # client 초기화
    client = GatewayClient(region_name=region)
    client.logger.setLevel(logging.INFO)

    # 이 튜토리얼에서 사용되는 Gateway 및 target 이름
    gateway_name = "TestGWforPolicyEngine"
    target_name = "RefundToolTarget"
    lambda_function_name = "RefundLambda"

    # 기존 설정 또는 gateway 확인
    existing_config = load_existing_config()
    gateway = None
    cognito_response = None
    lambda_arn = None

    if existing_config:
        print("📋 Found existing gateway_config.json")
        gateway_id = existing_config.get("gateway_id")

        # 기존 gateway 검색 시도
        print(f"  Checking if gateway '{gateway_id}' exists...")
        gateway = get_existing_gateway(region, gateway_id=gateway_id)

        if gateway:
            print(
                f"✓ Reusing existing gateway: {gateway.get('gatewayUrl', gateway_id)}\n"
            )
            # 사용 가능한 경우 기존 client_info 재사용
            # OAuth client 정보를 재생성하지 않고 기존 것 사용
            if existing_config.get("client_info"):
                cognito_response = {"client_info": existing_config["client_info"]}

            # Lambda ARN이 config에 저장되어 있는지 확인
            lambda_arn = existing_config.get("lambda_arn")
        else:
            print(f"  Gateway '{gateway_id}' not found or not ready.\n")

    # gateway가 아직 없으면 이름으로 존재하는지 확인
    if not gateway:
        print(f"🔍 Checking for existing gateway named '{gateway_name}'...")
        gateway = get_existing_gateway(region, gateway_name=gateway_name)
        if gateway:
            print(f"✓ Found existing gateway: {gateway.get('gatewayUrl')}\n")

    # Lambda 함수 생성 또는 가져오기
    if not lambda_arn:
        print("\n" + "=" * 60)
        print("Step 1: Setting up Refund Lambda function")
        print("=" * 60)
        lambda_arn = create_refund_lambda(region, lambda_function_name)
        print(f"✓ Lambda ARN: {lambda_arn}\n")
    else:
        print(f"\n✓ Using existing Lambda ARN: {lambda_arn}\n")

    # 기존 client_info가 없으면 OAuth authorizer 생성
    if not cognito_response:
        print("=" * 60)
        print("Step 2: Creating OAuth authorization server")
        print("=" * 60)
        # Cognito User Pool을 사용한 OAuth 2.0 authorizer 생성
        cognito_response = client.create_oauth_authorizer_with_cognito("TestGateway")
        print("✓ Authorization server created\n")

    # 기존 Gateway가 없으면 생성
    if not gateway:
        print("=" * 60)
        print("Step 3: Creating Gateway")
        print("=" * 60)
        gateway = client.create_mcp_gateway(
            name=gateway_name,
            role_arn=role_arn,
            authorizer_config=cognito_response.get("authorizer_config"),
            enable_semantic_search=True,
        )
        print(f"✓ Gateway created: {gateway['gatewayUrl']}\n")
    else:
        print("=" * 60)
        print("Step 3: Skipping gateway creation (reusing existing)")
        print("=" * 60 + "\n")

    # target이 이미 존재하는지 확인하고 없으면 추가
    print("=" * 60)
    print("Step 4: Adding Lambda target")
    print("=" * 60)

    gateway_id = gateway.get("gatewayId")
    print(f"  Gateway ID: {gateway_id}")
    print(f"  Target name: {target_name}")
    print(f"  Lambda ARN: {lambda_arn}")

    existing_target = get_existing_target(region, gateway_id, target_name)

    if existing_target:
        print(f"✓ Lambda target '{target_name}' already exists, reusing")
        print(f"  Target ID: {existing_target.get('targetId')}")
        lambda_target = {"gatewayArn": gateway.get("gatewayArn")}
    else:
        print(f"  Target '{target_name}' not found, creating...")
        try:
            # Lambda를 gateway의 target으로 등록 (tool schema 포함)
            lambda_target = client.create_mcp_gateway_target(
                gateway=gateway,
                name=target_name,
                target_type="lambda",
                target_payload={
                    "lambdaArn": lambda_arn,
                    "toolSchema": {"inlinePayload": REFUND_TOOL_SCHEMA},
                },
                credentials=None,
            )
            print(f"✓ Lambda target '{target_name}' created and attached to gateway\n")
        except Exception as exc:
            error_str = str(exc)
            # 동시 실행으로 인한 중복 생성 시도 처리
            if (
                "ConflictException" in str(type(exc).__name__)
                or "already exists" in error_str
            ):
                print(f"✓ Lambda target '{target_name}' already exists, reusing\n")
                lambda_target = {"gatewayArn": gateway.get("gatewayArn")}
            else:
                print(f"✗ Error creating target: {exc}")
                raise

    # 설정 저장
    config = {
        "gateway_url": gateway.get("gatewayUrl"),
        "gateway_id": gateway.get("gatewayId"),
        "gateway_arn": lambda_target.get("gatewayArn") or gateway.get("gatewayArn"),
        "region": region,
        "client_info": cognito_response.get("client_info"),
        "lambda_arn": lambda_arn,
    }

    with open("gateway_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print("\n" + "=" * 60)
    print("✅ Gateway setup complete!")
    print("=" * 60)
    print(f"Gateway URL: {config['gateway_url']}")
    print(f"Gateway ID: {config['gateway_id']}")
    print(f"Gateway ARN: {config['gateway_arn']}")
    print(f"Lambda ARN: {config['lambda_arn']}")
    print("\nConfiguration saved to: gateway_config.json")
    print("=" * 60)

    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Setup AgentCore Gateway with Lambda target for Policy tutorial"
    )
    parser.add_argument(
        "--region",
        type=str,
        default=None,
        help="AWS region (defaults to current session region or us-east-1)",
    )
    parser.add_argument(
        "--role-arn",
        type=str,
        default=None,
        help="IAM role ARN with trust relationship (creates one if not provided)",
    )

    args = parser.parse_args()
    setup_gateway(region=args.region, role_arn=args.role_arn)
