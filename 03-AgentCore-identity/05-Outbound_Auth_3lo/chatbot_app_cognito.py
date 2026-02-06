import streamlit as st
import os
import json
import requests
import urllib.parse
import logging
import re
import sys
import yaml
import uuid
import boto3
from oauth2_callback_server import store_token_in_oauth2_callback_server

logger = logging.getLogger()

qualifier = "DEFAULT"
# 채팅 기록을 위한 설정 가능한 컨텍스트 윈도우
CONTEXT_WINDOW = 10  # 컨텍스트에 포함할 턴 수 (사용자+어시스턴트 쌍)


def get_streamlit_url():
    try:
        # SageMaker Studio 메타데이터에서 domain_id와 space_name 추출
        with open("/opt/ml/metadata/resource-metadata.json", "r") as file:
            data = json.load(file)
            domain_id = data["DomainId"]
            space_name = data["SpaceName"]
    except FileNotFoundError:
        logger.info(
            "Resource-metadata.json file not found -- running outside SageMaker Studio"
        )
        domain_id = None
        space_name = None
        # sys.exit(1)
    except json.JSONDecodeError:
        logger.info("Error: Invalid JSON format in resource-metadata.json")
        sys.exit(1)
    except KeyError as e:
        logger.info(f"Error: Required key {e} not found in JSON")
        sys.exit(1)

    logger.info("Please use the following to login and test the Streamlit Application")
    logger.info("Username:       testuser")
    logger.info("Password:       MyPassword123!")
    if domain_id is not None:
        sagemaker_client = boto3.client("sagemaker")
        # SageMaker Space 정보를 조회하여 Streamlit URL 생성
        response = sagemaker_client.describe_space(
            DomainId=domain_id, SpaceName=space_name
        )

        streamlit_url = response["Url"] + "/proxy/8501/"
    else:
        # 로컬 환경에서 실행 시 localhost 사용
        streamlit_url = "http://localhost:8501"
    return streamlit_url


def build_context(messages, context_window=CONTEXT_WINDOW):
    # 최근 대화만 컨텍스트로 사용 (메모리 효율성)
    history = (
        messages[-context_window * 2 :]
        if len(messages) > context_window * 2
        else messages
    )
    context = ""
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        context += f"{role}: {msg['content']}\n"
    return context


def make_urls_clickable(text):
    """Convert URLs in text to clickable HTML links."""
    # HTTP/HTTPS URL 패턴 매칭
    url_pattern = r"https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?"

    def replace_url(match):
        url = match.group(0)
        # HTML 링크로 변환 (새 탭에서 열기)
        return f'<a href="{url}" target="_blank" style="color:#4fc3f7;text-decoration:underline;">{url}</a>'

    return re.sub(url_pattern, replace_url, text)


def load_bedrock_agentcore_config():
    """Load configuration from .bedrock_agentcore.yaml file."""
    config_path = ".bedrock_agentcore.yaml"

    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)

        # YAML에서 기본 agent 설정 추출
        default_agent = config.get("default_agent")
        if not default_agent:
            raise ValueError("default_agent not found in configuration")

        agents = config.get("agents", {})
        if default_agent not in agents:
            raise ValueError(
                f"Agent '{default_agent}' not found in agents configuration"
            )

        agent_config = agents[default_agent]
        bedrock_config = agent_config.get("bedrock_agentcore", {})
        auth_config = agent_config.get("authorizer_configuration", {})
        aws_config = agent_config.get("aws", {})

        # 필수 설정값 추출
        agent_session_id = bedrock_config.get("agent_session_id")
        agent_arn = bedrock_config.get("agent_arn")
        region = aws_config.get("region")

        # Cognito allowedClients에서 client_id 추출
        allowed_clients = []
        if "customJWTAuthorizer" in auth_config:
            allowed_clients = auth_config["customJWTAuthorizer"].get(
                "allowedClients", []
            )

        client_id = allowed_clients[0] if allowed_clients else None

        # 필수 필드 검증
        if not agent_arn:
            raise ValueError("agent_arn not found in bedrock_agentcore configuration")
        if not client_id:
            raise ValueError(
                "allowedClients not found or empty in authorizer_configuration"
            )
        if not region:
            raise ValueError("region not found in aws configuration")

        return {
            "agentSessionId": agent_session_id,
            "agentRuntimeArn": agent_arn,
            "client_id": client_id,
            "region": region,
        }

    except FileNotFoundError:
        raise FileNotFoundError(
            "Configuration file '.bedrock_agentcore.yaml' not found. Please ensure the configuration file exists in the current directory."
        )
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML configuration: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error loading configuration: {str(e)}")


# 설정 로드 (실패 시 에러 메시지 저장)
try:
    config = load_bedrock_agentcore_config()
    agentSessionId = config["agentSessionId"]
    agentRuntimeArn = config["agentRuntimeArn"]
    client_id = config["client_id"]
    region = config["region"]
except Exception as config_error:
    # 설정 로드 실패 시 None으로 초기화하고 main()에서 에러 표시
    agentSessionId = None
    agentRuntimeArn = None
    client_id = None
    region = None
    config_error_message = str(config_error)


class StreamingHttpBedrockAgentCoreClient:
    """Streaming version of HttpBedrockAgentCoreClient for real-time responses."""

    def __init__(self, region: str):
        """Initialize StreamingHttpBedrockAgentCoreClient."""
        self.region = region
        self.dp_endpoint = f"https://bedrock-agentcore.{region}.amazonaws.com"
        self.logger = logging.getLogger(
            f"bedrock_agentcore.streaming_http_runtime.{region}"
        )

    def invoke_endpoint_streaming(
        self,
        agent_arn: str,
        payload,
        session_id: str,
        bearer_token: str,
        endpoint_name: str = "DEFAULT",
    ):
        """Invoke agent endpoint and yield streaming response chunks."""
        # URL 인코딩을 위해 agent ARN escape 처리
        escaped_arn = urllib.parse.quote(agent_arn, safe="")

        # Bedrock AgentCore API endpoint URL 구성
        url = f"{self.dp_endpoint}/runtimes/{escaped_arn}/invocations"

        # HTTP 요청 헤더 설정
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
        }

        # payload를 JSON 객체로 변환
        try:
            body = json.loads(payload) if isinstance(payload, str) else payload
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 폴백
            self.logger.warning(
                "Failed to parse payload as JSON, wrapping in payload object"
            )
            body = {"payload": payload}

        try:
            # 스트리밍 모드로 HTTP POST 요청
            response = requests.post(
                url,
                params={"qualifier": endpoint_name},
                headers=headers,
                json=body,
                timeout=100,
                stream=True,
            )
            response.raise_for_status()

            # Server-Sent Events (SSE) 스트리밍 응답 처리
            if "text/event-stream" in response.headers.get("content-type", ""):
                # 스트리밍 응답을 라인별로 처리
                for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                    if line and line.startswith("data: "):
                        chunk = line[6:]  # "data: " 접두사 제거
                        if chunk.strip():  # 비어있지 않은 청크만 yield
                            yield chunk
            else:
                # 비스트리밍 응답인 경우 전체 콘텐츠 반환
                if response.content:
                    yield response.text

        except requests.exceptions.RequestException as e:
            self.logger.error("Failed to invoke agent endpoint: %s", str(e))
            raise


def ensure_aws_credentials():
    aws_profile = os.environ.get("AWS_PROFILE")
    if not aws_profile:
        st.warning(
            "AWS_PROFILE is not set in your environment. Please set AWS_PROFILE to the name of your AWS CLI profile before running."
        )
        st.stop()


def main():
    st.set_page_config(
        page_title="Bedrock Agentcore AI Chatbot",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    import boto3

    # 설정 로드 실패 시 에러 화면 표시
    if agentRuntimeArn is None or client_id is None or region is None:
        st.markdown(
            f"""
            <div style='max-width:600px;margin:40px auto 30px auto;padding:40px 40px 36px 40px;background:linear-gradient(145deg, #2d1b1b 0%, #3d2424 50%, #2d1b1b 100%);border-radius:24px;box-shadow:0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,87,87,0.3);border:2px solid rgba(255,87,87,0.4);position:relative;overflow:hidden;'>
                <div style='position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg, #ff5757, #ff4757, #ff3838);'></div>
                <div style='text-align:center;margin-bottom:32px;'>
                    <div style='font-size:4rem;margin-bottom:16px;color:#ff5757;'>⚠️</div>
                    <h2 style='color:#ff7675;font-family:Inter,Segoe UI,Arial,sans-serif;font-weight:700;margin:0;font-size:1.9rem;letter-spacing:-0.025em;'>Configuration Error</h2>
                    <p style='color:#fab1a0;font-size:1.1rem;margin:16px 0 0 0;line-height:1.5;'>Unable to load Bedrock AgentCore configuration</p>
                </div>
                <div style='background:rgba(255,87,87,0.1);border:1px solid rgba(255,87,87,0.3);border-radius:12px;padding:20px;margin:20px 0;'>
                    <h4 style='color:#ff7675;margin:0 0 12px 0;font-weight:600;'>Error Details:</h4>
                    <p style='color:#e17055;margin:0;font-family:monospace;font-size:0.95rem;word-break:break-word;'>{config_error_message}</p>
                </div>
                <div style='background:rgba(255,87,87,0.05);border:1px solid rgba(255,87,87,0.2);border-radius:12px;padding:20px;'>
                    <h4 style='color:#ff7675;margin:0 0 12px 0;font-weight:600;'>Required Configuration:</h4>
                    <ul style='color:#fab1a0;margin:0;padding-left:20px;'>
                        <li>Ensure <code>.bedrock_agentcore.yaml</code> exists in the current directory</li>
                        <li>Verify <code>agent_arn</code> is present in the bedrock_agentcore section</li>
                        <li>Verify <code>allowedClients</code> is present in the authorizer_configuration section</li>
                        <li>Verify <code>region</code> is present in the aws section</li>
                    </ul>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )
        st.stop()

    # 디버그: 인증 상태 확인
    if "cognito_access_token" not in st.session_state:
        st.session_state["cognito_access_token"] = None

    # Cognito 인증되지 않은 경우 로그인 화면 표시
    if st.session_state["cognito_access_token"] is None:
        st.markdown(
            """
            <div style='max-width:480px;margin:40px auto 30px auto;padding:40px 40px 36px 40px;background:linear-gradient(145deg, #1a1f2e 0%, #242b3d 50%, #1e2537 100%);border-radius:24px;box-shadow:0 8px 32px rgba(0,0,0,0.4), 0 0 0 1px rgba(100,181,246,0.1);border:1px solid rgba(100,181,246,0.2);position:relative;overflow:hidden;'>
                <div style='position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg, #64b5f6, #4fc3f7, #29b6f6, #0288d1);'></div>
                <div style='text-align:center;margin-bottom:32px;'>
                    <div style='font-size:3.5rem;margin-bottom:12px;background:linear-gradient(135deg, #64b5f6, #4fc3f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;display:inline-block;'>🔐</div>
                    <h2 style='color:#64b5f6;font-family:Inter,Segoe UI,Arial,sans-serif;font-weight:700;margin:0;font-size:1.8rem;letter-spacing:-0.025em;'>Bedrock AgentCore AI Login</h2>
                    <p style='color:#b3c5d7;font-size:1.1rem;margin:12px 0 0 0;line-height:1.5;'>Secure access to your AI assistant<br><span style="color:#7a8ca0;font-size:0.95em;">🔒 End-to-end encrypted • Never stored</span></p>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )
        with st.form("cognito_login_form"):
            st.markdown(
                """
                <style>
                .stTextInput>div>div>input {
                    background: linear-gradient(145deg, #1e2332 0%, #252b3e 100%);
                    color: #e8f4fd;
                    border-radius: 14px;
                    border: 2px solid transparent;
                    background-clip: padding-box;
                    font-size: 1.1rem;
                    padding: 0.8rem 1.3rem;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                }
                .stTextInput>div>div>input:focus {
                    border: 2px solid #4fc3f7;
                    box-shadow: 0 0 0 3px rgba(79, 195, 247, 0.1), 0 4px 12px rgba(0,0,0,0.2);
                    transform: translateY(-1px);
                }
                .stTextInput>label {
                    color: #64b5f6 !important;
                    font-weight: 600;
                    font-size: 1rem;
                    margin-bottom: 0.5rem;
                }
                .stButton>button {
                    background: linear-gradient(135deg, #4fc3f7 0%, #29b6f6 50%, #0288d1 100%);
                    color: #fff;
                    font-weight: 700;
                    border-radius: 14px;
                    font-size: 1.1rem;
                    padding: 0.8rem 2rem;
                    margin-top: 15px;
                    border: none;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    box-shadow: 0 4px 15px rgba(79, 195, 247, 0.3);
                    position: relative;
                    overflow: hidden;
                }
                .stButton>button:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 8px 25px rgba(79, 195, 247, 0.4);
                }
                .stButton>button::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                    transition: left 0.5s;
                }
                .stButton>button:hover::before {
                    left: 100%;
                }
                </style>
            """,
                unsafe_allow_html=True,
            )
            username = st.text_input("Username", key="cognito_username")
            password = st.text_input(
                "Password", type="password", key="cognito_password"
            )
            submitted = st.form_submit_button("Login")

        if submitted:
            with st.spinner("Authenticating with Cognito..."):
                try:
                    # Cognito Identity Provider를 통한 사용자 인증
                    client = boto3.client("cognito-idp", region_name=region)
                    resp = client.initiate_auth(
                        ClientId=client_id,
                        AuthFlow="USER_PASSWORD_AUTH",
                        AuthParameters={"USERNAME": username, "PASSWORD": password},
                    )
                    # 인증 성공 시 access token 저장
                    access_token = resp["AuthenticationResult"]["AccessToken"]
                    st.session_state["cognito_access_token"] = access_token
                    st.success(
                        "Cognito authentication successful! Redirecting to chatbot..."
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Cognito authentication failed: {e}")
        return  # 인증되지 않은 경우에만 여기서 반환

    # 향상된 시스템 상태 패널
    st.markdown(
        f"""
        <div style="position:fixed;top:15px;right:25px;z-index:9999;padding:18px 24px;background:linear-gradient(145deg, #1a1f2e 0%, #242b3d 100%);border-radius:16px;box-shadow:0 4px 20px rgba(0,0,0,0.3), 0 0 0 1px rgba(100,181,246,0.1);font-size:0.9em;color:#90caf9;font-family:Inter,Segoe UI,Arial,sans-serif;opacity:0.95;backdrop-filter:blur(10px);border:1px solid rgba(100,181,246,0.15);">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;color:#4fc3f7;font-weight:600;font-size:0.95em;">
            <span style="font-size:1.2em;">⚡</span> System Status
        </div>
        <div style="font-size:0.85em;line-height:1.4;">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="color:#b3c5d7;">Region:</span> 
                <span style="color:#fff;font-weight:500;">{region}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="color:#b3c5d7;">Agent:</span> 
                <span style="color:#4fc3f7;font-weight:500;">Active</span>
            </div>
            <div style="display:flex;justify-content:space-between;">
                <span style="color:#b3c5d7;">Session:</span> 
                <span style="color:#4fc3f7;font-weight:500;">Connected</span>
            </div>
        </div>
        <div style="position:absolute;bottom:0;left:0;right:0;height:2px;background:linear-gradient(90deg, #4fc3f7, #29b6f6);border-radius:0 0 16px 16px;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 향상된 CSS 스타일링
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        .stApp {
            background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 50%, #0f1419 100%) !important;
            font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important;
        }
        
        .user-bubble {
            background: linear-gradient(145deg, #242b3e 0%, #1e2537 100%);
            color: #e8f4fd;
            border-radius: 18px 18px 4px 18px;
            padding: 1rem 1.3rem;
            margin: 0.8rem 0;
            display: inline-block;
            border: 1px solid rgba(100, 181, 246, 0.3);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            font-weight: 500;
            line-height: 1.5;
            max-width: 85%;
            animation: slideInRight 0.3s ease-out;
        }
        
        .assistant-bubble {
            background: linear-gradient(145deg, #0a1929 0%, #0f2d47 50%, #0b1e36 100%);
            color: #e8f4fd;
            border-radius: 18px 18px 18px 4px;
            padding: 1rem 1.3rem;
            margin: 0.8rem 0;
            display: block;
            border: 1px solid rgba(79, 195, 247, 0.4);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
            white-space: pre-wrap;
            word-wrap: break-word;
            max-width: 90%;
            font-weight: 400;
            line-height: 1.6;
            animation: slideInLeft 0.3s ease-out;
        }
        
        .assistant-bubble.streaming {
            border: 1px solid rgba(79, 195, 247, 0.6);
            box-shadow: 0 6px 25px rgba(0, 0, 0, 0.4), 0 0 15px rgba(79, 195, 247, 0.2);
            animation: pulseGlow 2s infinite, slideInLeft 0.3s ease-out;
        }
        
        .thinking-bubble {
            background: linear-gradient(145deg, #0a1929 0%, #0f2d47 50%, #0b1e36 100%);
            color: #e8f4fd;
            border-radius: 18px;
            padding: 1rem 1.3rem;
            margin: 0.8rem 0;
            display: inline-block;
            border: 1px solid rgba(79, 195, 247, 0.5);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
            animation: thinking 1.5s infinite, slideInLeft 0.3s ease-out;
        }
        
        /* 애니메이션 */
        @keyframes slideInRight {
            from { opacity: 0; transform: translateX(20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        @keyframes slideInLeft {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        @keyframes pulseGlow {
            0%, 100% { box-shadow: 0 6px 25px rgba(0, 0, 0, 0.4), 0 0 15px rgba(79, 195, 247, 0.2); }
            50% { box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5), 0 0 20px rgba(79, 195, 247, 0.4); }
        }
        
        @keyframes thinking {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.02); opacity: 0.9; }
        }
        
        /* 향상된 타이포그래피 */
        h1, h2, h3, h4, h5, h6, p, label {
            color: #e8f4fd !important;
            font-family: 'Inter', 'Segoe UI', Arial, sans-serif !important;
        }
        
        h1 {
            background: linear-gradient(135deg, #64b5f6, #4fc3f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-weight: 700 !important;
        }
        
        /* 사이드바 스타일링 */
        .sidebar .sidebar-content {
            background: linear-gradient(145deg, #1a1f2e 0%, #0f1419 100%) !important;
        }
        
        /* 커스텀 스크롤바 */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: rgba(79, 195, 247, 0.1);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, #4fc3f7, #29b6f6);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(180deg, #29b6f6, #0288d1);
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # 향상된 사이드바
    st.sidebar.markdown(
        """
        <div style='text-align:center;padding:1.5rem 0;border-bottom:1px solid rgba(100,181,246,0.2);margin-bottom:1.5rem;'>
            <div style='font-size:3rem;margin-bottom:1rem;'>🤖</div>
            <h2 style='color:#64b5f6;font-weight:700;margin:0;font-size:1.4rem;'>Bedrock Agentcore AI</h2>
            <p style='color:#b3c5d7;font-size:0.9rem;margin:0.5rem 0 0 0;'>Conversational Intelligence</p>
        </div>
        
        <div style='margin-bottom:1.5rem;'>
            <h3 style='color:#4fc3f7;font-size:1rem;font-weight:600;margin-bottom:1rem;'>⚙️ Features</h3>
            <div style='display:flex;flex-direction:column;gap:0.5rem;'>
                <div style='display:flex;align-items:center;gap:10px;padding:0.5rem;background:rgba(79,195,247,0.1);border-radius:8px;'>
                    <span style='color:#4fc3f7;'>🔄</span>
                    <span style='color:#b3c5d7;font-size:0.9rem;'>Real-time Streaming</span>
                </div>
                <div style='display:flex;align-items:center;gap:10px;padding:0.5rem;background:rgba(79,195,247,0.1);border-radius:8px;'>
                    <span style='color:#4fc3f7;'>🧠</span>
                    <span style='color:#b3c5d7;font-size:0.9rem;'>Context Awareness</span>
                </div>
                <div style='display:flex;align-items:center;gap:10px;padding:0.5rem;background:rgba(79,195,247,0.1);border-radius:8px;'>
                    <span style='color:#4fc3f7;'>🔗</span>
                    <span style='color:#b3c5d7;font-size:0.9rem;'>Clickable URLs</span>
                </div>
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # 향상된 메인 헤더
    st.markdown(
        """
        <div style='text-align:center;padding:2rem 0 1rem 0;'>
            <div style='font-size:3.5rem;margin-bottom:0.5rem;'>🤖</div>
            <h1 style='margin:0;font-size:2.2rem;font-weight:700;'>Bedrock Agentcore AI Chatbot</h1>
            <p style='color:#b3c5d7;font-size:1.1rem;margin:0.5rem 0 0 0;'>Your intelligent conversation partner</p>
        </div>
        <div style='height:2px;background:linear-gradient(90deg, #4fc3f7, #29b6f6, #0288d1);border-radius:1px;margin:1.5rem 0;'></div>
    """,
        unsafe_allow_html=True,
    )

    # 채팅 기록 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agentSessionId" not in st.session_state:
        # agentSessionId가 없으면 UUID 생성
        st.session_state["agentSessionId"] = (
            agentSessionId if agentSessionId else str(uuid.uuid4())
        )

    # 앱 재실행 시 기존 채팅 메시지 표시
    messages_to_show = st.session_state.messages[:]
    # 어시스턴트 응답 대기 중이면 마지막 사용자 메시지는 제외 (아래에서 별도 표시)
    if (
        st.session_state.get("pending_assistant", False)
        and messages_to_show
        and messages_to_show[-1]["role"] == "user"
    ):
        messages_to_show = messages_to_show[:-1]
    for message in messages_to_show:
        bubble_class = (
            "user-bubble" if message["role"] == "user" else "assistant-bubble"
        )
        emoji = "🧑‍💻" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "elapsed" in message:
                clickable_content = make_urls_clickable(message["content"])
                st.markdown(
                    f'<div class="{bubble_class}">{emoji} {clickable_content}<br><span style="font-size:0.9em;color:#888;">⏱️ Response time: {message["elapsed"]:.2f} seconds</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                if message["role"] == "assistant":
                    clickable_content = make_urls_clickable(message["content"])
                    st.markdown(
                        f'<div class="{bubble_class}">{emoji} {clickable_content}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<span class="{bubble_class}">{emoji} {message["content"]}</span>',
                        unsafe_allow_html=True,
                    )

    # 어시스턴트를 기다리지 않는 경우에만 사용자 입력 수락
    if "pending_assistant" not in st.session_state:
        st.session_state["pending_assistant"] = False

    if not st.session_state["pending_assistant"]:
        prompt = st.chat_input("What would you like to know?")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state["pending_assistant"] = True
            st.rerun()

    # 어시스턴트 응답 대기 중이고 마지막 메시지가 사용자 메시지인 경우 응답 처리
    if (
        st.session_state["pending_assistant"]
        and st.session_state.messages
        and st.session_state.messages[-1]["role"] == "user"
    ):
        user_msg = st.session_state.messages[-1]["content"]
        with st.chat_message("user"):
            st.markdown(
                f'<span class="user-bubble">🧑‍💻 {user_msg}</span>',
                unsafe_allow_html=True,
            )
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            import time

            start_time = time.time()
            accumulated_response = ""

            try:
                # 스트리밍 클라이언트 설정
                session_id = st.session_state.get("agentSessionId")
                context = build_context(st.session_state.messages, CONTEXT_WINDOW)
                payload = json.dumps({"prompt": context})
                bearer_token = st.session_state.get("cognito_access_token")
                # OAuth2 callback server에 token 저장
                store_token_in_oauth2_callback_server(bearer_token)

                streaming_client = StreamingHttpBedrockAgentCoreClient(region)

                # 초기 생각 중 상태 표시 (펄스 애니메이션)
                message_placeholder.markdown(
                    '<span class="thinking-bubble">🤖 💭 Bedrock Agentcore is thinking...</span>',
                    unsafe_allow_html=True,
                )

                # 애니메이션으로 응답 스트리밍
                chunk_count = 0
                formatted_response = ""

                for chunk in streaming_client.invoke_endpoint_streaming(
                    agent_arn=agentRuntimeArn,
                    payload=payload,
                    session_id=session_id,
                    bearer_token=bearer_token,
                    endpoint_name=qualifier,
                ):
                    if chunk.strip():  # 비어있지 않은 청크만 처리
                        accumulated_response += chunk
                        chunk_count += 1

                        # "End agent execution" 마커로 응답 완료 확인
                        if '"End agent execution"' in accumulated_response:
                            # 처리 중 상태 표시
                            message_placeholder.markdown(
                                '<span class="thinking-bubble">🤖 🔄 Processing response...</span>',
                                unsafe_allow_html=True,
                            )

                            # JSON 파싱하여 실제 응답 텍스트 추출
                            try:
                                # Begin/End 마커 사이의 JSON 추출
                                begin_marker = '"Begin agent execution"'
                                end_marker = '"End agent execution"'

                                begin_pos = accumulated_response.find(begin_marker)
                                end_pos = accumulated_response.find(end_marker)

                                if begin_pos != -1 and end_pos != -1:
                                    # 마커 사이의 JSON 부분 추출
                                    json_part = accumulated_response[
                                        begin_pos + len(begin_marker) : end_pos
                                    ].strip()

                                    # JSON 객체 시작 위치 찾기
                                    json_start = json_part.find('{"role":')
                                    if json_start != -1:
                                        json_str = json_part[json_start:]
                                        # 중괄호 카운팅으로 JSON 객체 끝 찾기
                                        brace_count = 0
                                        json_end = -1
                                        for i, char in enumerate(json_str):
                                            if char == "{":
                                                brace_count += 1
                                            elif char == "}":
                                                brace_count -= 1
                                                if brace_count == 0:
                                                    json_end = i + 1
                                                    break

                                        if json_end != -1:
                                            json_str = json_str[:json_end]
                                            logger.info(
                                                f"Extracted JSON: {json_str}"
                                            )  # 디버그 출력
                                            response_data = json.loads(json_str)

                                            # JSON 구조에서 텍스트 추출
                                            if (
                                                "content" in response_data
                                                and len(response_data["content"]) > 0
                                                and "text"
                                                in response_data["content"][0]
                                            ):
                                                formatted_response = response_data[
                                                    "content"
                                                ][0]["text"]
                                                logger.info(
                                                    f"Extracted text: {formatted_response}"
                                                )  # 디버그 출력

                            except (json.JSONDecodeError, KeyError, IndexError) as e:
                                logger.info(f"JSON parsing error: {e}")
                                logger.info(
                                    f"Accumulated response: {accumulated_response}"
                                )
                                # JSON 파싱 실패 시 원본 응답 사용
                                formatted_response = accumulated_response
                            break

                        # 아직 응답이 완료되지 않은 경우 스트리밍 텍스트 표시
                        else:
                            # 타이핑 효과를 위한 커서 추가
                            streaming_text = accumulated_response
                            if (
                                chunk_count % 3 == 0
                            ):  # 일부 청크마다 커서 추가
                                streaming_text += ""

                            # URL을 클릭 가능하게 변환하여 표시
                            clickable_streaming_text = make_urls_clickable(
                                streaming_text
                            )
                            message_placeholder.markdown(
                                f'<div class="assistant-bubble streaming typing-cursor">🤖 {clickable_streaming_text}</div>',
                                unsafe_allow_html=True,
                            )
                            # 부드러운 스트리밍 효과를 위한 짧은 지연
                            time.sleep(0.02)

                # 최종 응답 표시 (응답 시간 포함)
                elapsed = time.time() - start_time
                answer = (
                    formatted_response
                    if formatted_response
                    else (
                        accumulated_response
                        if accumulated_response
                        else "No response received"
                    )
                )
                clickable_answer = make_urls_clickable(answer)
                message_placeholder.markdown(
                    f'<div class="assistant-bubble">🤖 {clickable_answer}<br><span style="font-size:0.9em;color:#888;">⏱️ Response time: {elapsed:.2f} seconds</span></div>',
                    unsafe_allow_html=True,
                )

            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                message_placeholder.markdown(
                    f'<div class="assistant-bubble">🤖 ❌ {error_msg}</div>',
                    unsafe_allow_html=True,
                )
                answer = error_msg
                elapsed = time.time() - start_time

            # 세션 상태에 최종 응답 저장
            final_answer = answer if "answer" in locals() else accumulated_response
            st.session_state.messages.append(
                {"role": "assistant", "content": final_answer, "elapsed": elapsed}
            )
            st.session_state["pending_assistant"] = False
            st.rerun()


if __name__ == "__main__":
    main()
