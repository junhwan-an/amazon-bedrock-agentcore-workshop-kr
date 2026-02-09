"""
Lambda 함수를 배포하고 ARN을 config.json에 저장합니다

사용법:
    python deploy_lambdas.py [role_arn]

예시:
    # 기존 role 사용
    python deploy_lambdas.py arn:aws:iam::123456789012:role/MyLambdaRole

    # 새 role 자동 생성
    python deploy_lambdas.py
"""

import boto3
import zipfile
import io
import os
import json
import sys
import time


def get_or_create_lambda_role(iam_client):
    """Lambda 실행을 위한 IAM role을 가져오거나 생성합니다"""
    role_name = "AgentCoreLambdaExecutionRole"

    try:
        response = iam_client.get_role(RoleName=role_name)
        print(f"   ✅ Using existing IAM role: {role_name}")
        # 반환값: (role ARN, 새로 생성 여부)
        return response["Role"]["Arn"], False
    except iam_client.exceptions.NoSuchEntityException:
        print(f"   📝 Creating IAM role: {role_name}")

        # Trust policy: Lambda 서비스가 이 role을 assume할 수 있도록 허용
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }

        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Execution role for AgentCore Lambda functions",
        )

        # CloudWatch Logs 권한을 포함한 기본 Lambda 실행 policy 연결
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )

        print(f"   ✅ IAM role created: {role_name}")
        print("   ⏳ Waiting 10 seconds for IAM propagation...")
        return response["Role"]["Arn"], True


def deploy_lambda(lambda_client, function_name, js_file, role_arn):
    """JS 파일로부터 Lambda 함수를 배포합니다"""

    print(f"📦 Deploying {function_name}...")

    # 스크립트와 같은 디렉토리에서 JS 파일 경로 찾기
    script_dir = os.path.dirname(os.path.abspath(__file__))
    js_path = os.path.join(script_dir, js_file)

    with open(js_path, "r") as f:
        code_content = f.read()

    # Lambda 배포를 위해 메모리에서 zip 파일 생성 (index.mjs는 ES module 형식)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("index.mjs", code_content)

    zip_buffer.seek(0)
    zip_content = zip_buffer.read()

    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime="nodejs20.x",
            Role=role_arn,
            Handler="index.handler",
            Code={"ZipFile": zip_content},
            Description=f"AgentCore {function_name}",
            Timeout=30,
            MemorySize=256,
        )

        print("   ✅ Lambda created")
        print(f"   ARN: {response['FunctionArn']}")
        return response["FunctionArn"]

    except lambda_client.exceptions.ResourceConflictException:
        # 함수가 이미 존재하면 코드만 업데이트
        print("   ℹ️  Function exists, updating code...")

        response = lambda_client.update_function_code(
            FunctionName=function_name, ZipFile=zip_content
        )

        print("   ✅ Code updated")
        print(f"   ARN: {response['FunctionArn']}")
        return response["FunctionArn"]

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def save_config(lambda_arns, output_file="config.json"):
    """Lambda ARN을 Getting-Started 디렉토리의 config.json에 저장합니다"""

    # 현재 스크립트 위치: lambda-target-setup/
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 상위 디렉토리 2단계 이동: lambda-target-setup -> scripts -> Getting-Started
    getting_started_dir = os.path.dirname(os.path.dirname(script_dir))
    config_path = os.path.join(getting_started_dir, output_file)

    config = {"lambdas": lambda_arns, "region": "us-west-2"}

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n💾 Configuration saved to: {config_path}")


def main():
    print("🚀 Deploying Lambda Functions\n")
    print("=" * 70)

    # boto3 클라이언트 초기화
    lambda_client = boto3.client("lambda", region_name="us-west-2")
    iam_client = boto3.client("iam", region_name="us-west-2")

    # 커맨드라인 인자로 role ARN이 제공되었는지 확인
    if len(sys.argv) >= 2:
        role_arn = sys.argv[1]

        # ARN 형식 검증
        if not role_arn.startswith("arn:aws:iam::"):
            print(f"\n❌ Error: Invalid role ARN format: {role_arn}")
            print("Expected format: arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME")
            print("\n" + "=" * 70)
            sys.exit(1)

        print(f"\n🔐 Using provided IAM role: {role_arn}")
        print()
        newly_created = False
    else:
        # role이 제공되지 않으면 자동으로 생성
        print("\n🔐 No role provided, setting up IAM role...")
        role_arn, newly_created = get_or_create_lambda_role(iam_client)
        print()

        # IAM role이 방금 생성된 경우 AWS 전파 대기 (eventual consistency)
        if newly_created:
            time.sleep(10)

    # 배포할 Lambda 함수 목록 (함수명, JS 파일명)
    functions = [
        ("ApplicationTool", "application_tool.js"),
        ("ApprovalTool", "approval_tool.js"),
        ("RiskModelTool", "risk_model_tool.js"),
    ]

    lambda_arns = {}

    for function_name, js_file in functions:
        arn = deploy_lambda(lambda_client, function_name, js_file, role_arn)
        if arn:
            lambda_arns[function_name] = arn
        print()
        # Lambda API rate limit 방지를 위한 짧은 대기
        time.sleep(1)

    # 배포된 Lambda ARN을 config.json에 저장
    if lambda_arns:
        save_config(lambda_arns)

    print("=" * 70)
    print(f"\n✅ Deployment complete! {len(lambda_arns)}/3 functions deployed.")
    print("\nLambda ARNs have been saved to config.json")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
