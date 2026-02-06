#!/usr/bin/env python3
"""
녹화 및 재생 기능이 포함된 완전한 Browser 예제

이 예제는 전체 Bedrock AgentCore browser 워크플로우를 보여줍니다:
1. 녹화 기능이 활성화된 browser 생성
2. Browser 세션 시작
3. 제어 획득/해제 기능이 있는 라이브 뷰
4. S3에 자동으로 저장되는 녹화
5. 세션 재생 뷰어로 녹화 보기

환경 변수:
    AWS_REGION          - AWS 리전 (기본값: us-west-2)
    BEDROCK_AGENTCORE_ROLE_ARN    - Bedrock AgentCore 실행을 위한 IAM role ARN (설정되지 않은 경우 기본 패턴 사용)
    RECORDING_BUCKET    - 녹화를 위한 S3 bucket (기본값: session-record-test-{account_id})
    RECORDING_PREFIX    - 녹화를 위한 S3 prefix (기본값: replay-data)
    BEDROCK_AGENTCORE_STAGE       - Bedrock AgentCore stage (기본값: prod)

요구사항:
    - Bedrock AgentCore browser를 생성/관리할 수 있는 권한이 있는 AWS 자격 증명
    - S3 및 browser 작업에 대한 권한이 있는 실행 role
    - 적절한 권한이 있는 S3 bucket
"""

import os
import sys
import time
import json
import uuid
import base64
import secrets
import tempfile
import threading
import webbrowser
import socket
import signal
import shutil
import gzip
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import mimetypes

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import ClientError, NoCredentialsError
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Tool import
from bedrock_agentcore.tools.browser_client import BrowserClient
from bedrock_agentcore._utils.endpoints import get_control_plane_endpoint
from .browser_viewer_replay import BrowserViewerServer
from .session_replay_viewer import S3DataSource, SessionReplayViewer, SessionReplayHandler

# Console 초기화
console = Console()

# 환경 변수에서 기본값과 함께 설정 가져오기
REGION = os.environ.get("AWS_REGION", "us-west-2")
BEDROCK_AGENTCORE_STAGE = os.environ.get("BEDROCK_AGENTCORE_STAGE", "prod")

# 제공되지 않은 경우 STS에서 account ID 가져오기
try:
    sts_client = boto3.client('sts')
    ACCOUNT_ID = sts_client.get_caller_identity()["Account"]
    console.print(f"[dim]Using AWS Account ID: {ACCOUNT_ID}[/dim]")
except Exception as e:
    console.print(f"[yellow]Warning: Could not determine AWS Account ID: {e}[/yellow]")
    console.print("[yellow]Please set BEDROCK_AGENTCORE_ROLE_ARN environment variable manually.[/yellow]")
    ACCOUNT_ID = "YOUR_ACCOUNT_ID"  # BEDROCK_AGENTCORE_ROLE_ARN이 설정되지 않은 경우에만 사용됨

# role ARN 및 bucket 이름 설정
ROLE_ARN = os.environ.get("BEDROCK_AGENTCORE_ROLE_ARN", f"arn:aws:iam::{ACCOUNT_ID}:role/BedrockAgentCoreAdmin")
BUCKET_PREFIX = os.environ.get("RECORDING_BUCKET_PREFIX", "session-record-test")
BUCKET_NAME = os.environ.get("RECORDING_BUCKET", f"{BUCKET_PREFIX}-{ACCOUNT_ID}")
S3_PREFIX = os.environ.get("RECORDING_PREFIX", "replay-data")

def create_browser_with_recording():
    """Control Plane API를 사용하여 녹화 기능이 활성화된 browser 생성"""
    
    # 1단계: Control Plane endpoint 가져오기 및 client 생성
    control_plane_url = get_control_plane_endpoint(REGION)
    console.print(f"Using Control Plane URL: [dim]{control_plane_url}[/dim]")
    
    control_client = boto3.client(
        "bedrock-agentcore-control",
        region_name=REGION,
        endpoint_url=control_plane_url
    )
    
    # 고유한 browser 이름 및 client token 생성
    browser_name = f"Browser_{uuid.uuid4().hex[:8]}"
    client_token = str(uuid.uuid4())
    
    # 녹화 설정과 함께 browser 생성
    console.print(f"\n🔍 Creating browser with recording enabled")
    console.print(f"  - Name: {browser_name}")
    console.print(f"  - Role ARN: {ROLE_ARN}")
    console.print(f"  - S3 Location: s3://{BUCKET_NAME}/{S3_PREFIX}/")
    
    try:
        create_response = control_client.create_browser(
            name=browser_name,
            networkConfiguration={
                "networkMode": "PUBLIC"
            },
            executionRoleArn=ROLE_ARN,
            recording={
                "enabled": True,
                "s3Location": {
                    "bucket": BUCKET_NAME,
                    "prefix": S3_PREFIX
                }
            },
            clientToken=client_token
        )
        
        browser_id = create_response['browserId']
        browser_arn = create_response.get('browserArn', 'Not available')
        status = create_response.get('status', 'Unknown')
        
        console.print(f"✅ Created browser: {browser_id}")
        console.print(f"  ARN: [dim]{browser_arn}[/dim]")
        console.print(f"  Status: {status}")
        
        # 디버깅을 위한 녹화 설정 출력
        if 'recording' in create_response:
            console.print(f"📹 Recording config: {create_response['recording']}")
        else:
            console.print("⚠️ No recording config in response!")
        
        # 2단계: Data Plane client 생성 및 browser 세션 시작
        console.print("\n📱 Starting browser session with the new browser...")
        
        # Data Plane client 생성
        data_plane_url = f"https://bedrock-agentcore.{REGION}.amazonaws.com"
        console.print(f"Using Data Plane URL: [dim]{data_plane_url}[/dim]")
        
        data_client = boto3.client(
            "bedrock-agentcore",
            region_name=REGION,
            endpoint_url=data_plane_url
        )
        
        # browser_id를 사용하여 browser 세션 시작
        session_response = data_client.start_browser_session(
            browserIdentifier=browser_id,
            name=f"Session-{uuid.uuid4().hex[:8]}",
            sessionTimeoutSeconds=3600  # 1시간
        )
        
        session_id = session_response["sessionId"]
        console.print(f"✅ Started session: {session_id}")
        
        # automation stream 정보 추출
        streams = session_response.get("streams", {})
        automation_stream = streams.get("automationStream")
        
        if automation_stream:
            console.print(f"✅ Found automation stream information")
        else:
            console.print("⚠️ No automation stream found in response")
        
        # 이제 BrowserClient를 생성하고 속성 설정
        browser_client = BrowserClient(region=REGION)
        browser_client.identifier = browser_id
        browser_client.session_id = session_id
        
        # browser가 완전히 프로비저닝될 때까지 대기
        console.print("⏳ Waiting for browser to become available...")
        time.sleep(5)
        
        return browser_client, {
            "bucket": BUCKET_NAME,
            "prefix": S3_PREFIX,
            "browser_id": browser_id,
            "session_id": session_id
        }
        
    except Exception as e:
        console.print(f"❌ Error creating or starting browser: {str(e)}")
        console.print("📋 Details:")
        import traceback
        traceback.print_exc()
        raise

def get_sigv4_headers(region: str, session_id: str) -> Dict[str, str]:
    """WebSocket 연결을 위한 SigV4 인증 헤더 생성"""
    # WebSocket 연결을 위한 Host
    host = f"https://bedrock-agentcore-control.{REGION}.amazonaws.com"
    path = f"/browser-streams/aws.browser.v1/sessions/{session_id}/live-view"
    
    # SigV4 서명을 위한 AWS 자격 증명 가져오기
    boto_session = boto3.Session()
    credentials = boto_session.get_credentials().get_frozen_credentials()  # 불변 자격 증명 객체 반환
    
    # 요청을 위한 타임스탬프 생성
    timestamp = datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    
    # 서명을 위한 AWS 요청 생성
    request = AWSRequest(
        method='GET',
        url=f'https://{host}{path}',
        headers={
            'host': host,
            'x-amz-date': timestamp
        }
    )
    
    # SigV4로 요청 서명 (AWS API 인증 방식)
    auth = SigV4Auth(credentials, "bedrock-agentcore", region)
    auth.add_auth(request)
    
    # 랜덤 WebSocket key 생성 (WebSocket handshake 프로토콜 요구사항)
    ws_key = base64.b64encode(secrets.token_bytes(16)).decode()
    
    # WebSocket 헤더 구성
    headers = {
        'Host': host,
        'X-Amz-Date': timestamp,
        'Authorization': request.headers['Authorization'],
        'Upgrade': 'websocket',
        'Connection': 'Upgrade',
        'Sec-WebSocket-Version': '13',
        'Sec-WebSocket-Key': ws_key,
        'User-Agent': 'Bedrock-AgentCore-BrowserViewer/1.0'
    }
    
    # 보안 토큰이 있는 경우 추가 (임시 자격 증명 사용 시)
    if credentials.token:
        headers['X-Amz-Security-Token'] = credentials.token
    
    return headers

def run_live_viewer_with_control(browser_client):
    """제어 획득/해제 기능이 있는 라이브 뷰어 실행"""
    
    print("\n🖥️  Starting Live Viewer...")
    print("Features available:")
    print("  - 🎮 Take Control: Disable automation and interact manually")
    print("  - 🚫 Release Control: Return control to automation")
    print("  - 📐 Resize display: 720p, 900p, 1080p, 1440p")
    
    # 뷰어 시작
    viewer = BrowserViewerServer(browser_client, port=8000)
    viewer_url = viewer.start(open_browser=True)
    
    print(f"\n✅ Live viewer running at: {viewer_url}")
    print("\nYou can now:")
    print("1. Take control and browse manually")
    print("2. Navigate to different websites")
    print("3. All actions are being recorded to S3")
    print("\nPress Ctrl+C when done to view recordings")
    
    try:
        # 사용자가 중지할 때까지 계속 실행
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping live viewer...")

def view_recordings(s3_location):
    """커스텀 SessionReplayViewer로 녹화된 세션을 직접 보기"""
    
    print("\n📼 Checking for recordings in S3...")
    print(f"Location: s3://{s3_location['bucket']}/{s3_location['prefix']}/")
    
    # S3 client 생성
    s3 = boto3.client('s3')
    
    # 녹화가 업로드될 때까지 조금 더 대기
    print("⏳ Waiting for recordings to be uploaded to S3 (30 seconds)...")
    time.sleep(30)
    
    try:
        # 먼저, 모든 객체의 플랫 리스트를 가져와서 세션 디렉토리 찾기
        response = s3.list_objects_v2(
            Bucket=s3_location['bucket'],
            Prefix=s3_location['prefix']
        )
        
        if 'Contents' not in response:
            print("No objects found in S3 location")
            return
            
        # metadata.json을 포함하는 모든 고유 디렉토리 이름 가져오기
        session_dirs = set()
        metadata_files = []
        
        for obj in response['Contents']:
            key = obj['Key']
            if 'metadata.json' in key:
                # 경로에서 세션 디렉토리 추출
                # 예: replay-data/01JZV5RW9FEV3GC5RPG8PYGXFR/metadata.json
                session_dir = key.split('/')[-2]
                session_dirs.add(session_dir)
                metadata_files.append(key)
                print(f"Found session with metadata: {session_dir}")
        
        if not session_dirs:
            print("No session directories with metadata.json found")
            return
            
        # 최신 세션을 찾기 위해 세션 디렉토리 정렬
        # 세션 ID가 시간순으로 정렬되어 있다고 가정
        session_dirs = sorted(list(session_dirs))
        latest_session = session_dirs[-1]
        print(f"Using latest session: {latest_session}")
        
        # 사용하기 전에 먼저 커스텀 S3 data source 클래스 정의
        class CustomS3DataSource:
            """알려진 구조를 가진 S3 녹화를 위한 커스텀 data source"""
            
            def __init__(self, bucket, prefix, session_id):
                self.s3_client = boto3.client('s3')
                self.bucket = bucket
                self.prefix = prefix
                self.session_id = session_id
                self.session_prefix = f"{prefix}/{session_id}"
                self.temp_dir = Path(tempfile.mkdtemp(prefix='bedrock_agentcore_replay_'))  # 임시 디렉토리 생성
                
            def cleanup(self):
                """임시 파일 정리"""
                if self.temp_dir.exists():
                    shutil.rmtree(self.temp_dir)
            
            def list_recordings(self):
                """녹화 목록을 직접 나열"""
                recordings = []
                
                # 녹화에 대한 세부 정보를 얻기 위해 metadata 가져오기
                metadata = {}
                try:
                    metadata_key = f"{self.session_prefix}/metadata.json"
                    print(f"Fetching metadata from: {metadata_key}")
                    response = self.s3_client.get_object(Bucket=self.bucket, Key=metadata_key)
                    metadata = json.loads(response['Body'].read().decode('utf-8'))
                    print(f"✅ Found metadata: {metadata}")
                except Exception as e:
                    print(f"⚠️ Could not get metadata: {e}")
                
                # 이벤트 수를 세기 위해 batch 파일 나열
                batch_files = []
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket,
                    Prefix=f"{self.session_prefix}/batch-"
                )
                
                if 'Contents' in response:
                    batch_files = [obj['Key'] for obj in response['Contents']]
                    print(f"✅ Found {len(batch_files)} batch files")
                
                # 녹화 항목 생성
                timestamp = int(time.time() * 1000)  # 기본값은 현재 시간
                duration = 0
                event_count = 0
                
                # 타임스탬프를 올바르게 파싱
                if 'startTime' in metadata:
                    try:
                        # ISO 형식 처리 (예: 2026-02-05T08:04:38.112Z)
                        if isinstance(metadata['startTime'], str):
                            dt = datetime.fromisoformat(metadata['startTime'].replace('Z', '+00:00'))
                            timestamp = int(dt.timestamp() * 1000)  # milliseconds로 변환
                        else:
                            timestamp = metadata['startTime']
                    except Exception as e:
                        print(f"⚠️ Error parsing startTime: {e}")
                        
                # 다른 duration 필드 시도
                if 'duration' in metadata:
                    duration = metadata['duration']
                elif 'durationMs' in metadata:
                    duration = metadata['durationMs']
                    
                # 다른 이벤트 수 필드 시도
                if 'eventCount' in metadata:
                    event_count = metadata['eventCount']
                elif 'totalEvents' in metadata:
                    event_count = metadata['totalEvents']
                
                # 올바른 datetime 형식 사용
                date_string = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
                
                recordings.append({
                    'id': self.session_id,
                    'sessionId': self.session_id,
                    'timestamp': timestamp,
                    'date': date_string,
                    'events': event_count,
                    'duration': duration
                })
                
                return recordings
            
            def download_recording(self, recording_id):
                """S3에서 녹화 다운로드"""
                print(f"Downloading recording: {recording_id}")
                
                recording_dir = self.temp_dir / recording_id
                recording_dir.mkdir(exist_ok=True)
                
                try:
                    # metadata 가져오기
                    metadata = {}
                    try:
                        metadata_key = f"{self.session_prefix}/metadata.json"
                        response = self.s3_client.get_object(Bucket=self.bucket, Key=metadata_key)
                        metadata = json.loads(response['Body'].read().decode('utf-8'))
                        print(f"✅ Downloaded metadata: {metadata}")
                    except Exception as e:
                        print(f"⚠️ No metadata found: {e}")
                    
                    # 가능한 경우 metadata에서 batch 파일 가져오기
                    batch_files = []
                    if 'batches' in metadata and isinstance(metadata['batches'], list):
                        for batch in metadata['batches']:
                            if 'file' in batch:
                                batch_files.append(f"{self.session_prefix}/{batch['file']}")
                    
                    # metadata에서 batch 파일을 찾지 못한 경우, 직접 찾기
                    if not batch_files:
                        response = self.s3_client.list_objects_v2(
                            Bucket=self.bucket,
                            Prefix=f"{self.session_prefix}/batch-"
                        )
                        
                        if 'Contents' in response:
                            batch_files = [obj['Key'] for obj in response['Contents']]
                    
                    all_events = []
                    print(f"Processing {len(batch_files)} batch files: {batch_files}")
                    
                    for key in batch_files:
                        try:
                            print(f"Downloading batch file: {key}")
                            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
                            
                            # gzip으로 압축된 JSON 라인으로 읽기 시도
                            with gzip.GzipFile(fileobj=io.BytesIO(response['Body'].read())) as gz:
                                content = gz.read().decode('utf-8')
                                print(f"Read {len(content)} bytes of content")
                                
                                # 각 라인을 JSON 이벤트로 처리 (JSONL 형식)
                                for line in content.splitlines():
                                    if line.strip():
                                        try:
                                            event = json.loads(line)
                                            # 이벤트 검증 (필수 필드 확인)
                                            if 'type' in event and 'timestamp' in event:
                                                all_events.append(event)
                                            else:
                                                print(f"⚠️ Skipping invalid event (missing required fields)")
                                        except json.JSONDecodeError as je:
                                            print(f"⚠️ Invalid JSON in line: {line[:50]}...")
                                            
                                print(f"  Added {len(all_events)} events")
                                            
                        except Exception as e:
                            print(f"⚠️ Error processing file {key}: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    print(f"✅ Loaded {len(all_events)} events")
                    
                    # 이벤트가 로드되지 않은 경우, 샘플 이벤트 생성
                    if len(all_events) < 2:
                        print("⚠️ Insufficient events, creating sample events for testing")
                        all_events = [
                            {"type": 2, "timestamp": timestamp, "data": {"href": "https://example.com", "width": 1280, "height": 720}} 
                            for timestamp in range(int(time.time() * 1000), int(time.time() * 1000) + 10000, 1000)
                        ]
                        # 최소한의 DOM 스냅샷 이벤트 추가 (rrweb 재생을 위한 필수 이벤트)
                        all_events.append({
                            "type": 4, 
                            "timestamp": int(time.time() * 1000) + 1000,
                            "data": {
                                "node": {
                                    "type": 1,
                                    "childNodes": [
                                        {"type": 2, "tagName": "html", "attributes": {}, "childNodes": [
                                            {"type": 2, "tagName": "body", "attributes": {}, "childNodes": [
                                                {"type": 3, "textContent": "Sample content"}
                                            ]}
                                        ]}
                                    ]
                                }
                            }
                        })
                    
                    # 파싱된 녹화 반환
                    return {
                        'metadata': metadata,
                        'events': all_events
                    }
                    
                except Exception as e:
                    print(f"❌ Error downloading recording: {e}")
                    import traceback
                    traceback.print_exc()
                    return None

        # JSON 응답 문제를 수정하는 커스텀 HTTP handler 생성
        class CustomSessionReplayHandler(SessionReplayHandler):
            """세션 재생 뷰어를 위한 커스텀 HTTP 요청 handler"""
            
            def serve_recordings_list(self):
                """녹화 목록 반환 - HTML 응답 문제 수정"""
                try:
                    recordings = self.data_source.list_recordings()
                    response = json.dumps(recordings)
                    
                    # 반환하는 내용을 확인하기 위한 디버그 출력
                    print(f"Serving recordings list: {response[:100]}...")
                    
                    # 적절한 content type 및 헤더 보장
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(response)))
                    # 문제를 방지하기 위한 CORS 헤더 추가 (cross-origin 요청 허용)
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', '*')
                    self.end_headers()
                    
                    # 응답을 바이트로 작성
                    self.wfile.write(response.encode('utf-8'))
                    
                except Exception as e:
                    print(f"❌ Error in serve_recordings_list: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # 빈 녹화 배열과 함께 적절한 오류 응답을 JSON으로 반환
                    error_response = json.dumps({
                        "error": str(e),
                        "recordings": []
                    })
                    self.send_response(200)  # client가 오류를 처리할 수 있도록 200 사용
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(error_response)))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(error_response.encode('utf-8'))
            
            def download_and_serve_recording(self, recording_id):
                """녹화 다운로드 및 제공 - HTML 응답 문제 수정"""
                try:
                    recording_data = self.data_source.download_recording(recording_id)
                    
                    if recording_data:
                        response = json.dumps({
                            'success': True,
                            'data': recording_data
                        })
                        
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Content-Length', str(len(response)))
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(response.encode('utf-8'))
                    else:
                        error_response = json.dumps({
                            'success': False,
                            'error': 'Recording not found'
                        })
                        self.send_response(404)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Content-Length', str(len(error_response)))
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(error_response.encode('utf-8'))
                        
                except Exception as e:
                    print(f"❌ Error in download_and_serve_recording: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    error_response = json.dumps({
                        'success': False,
                        'error': str(e)
                    })
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(error_response)))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(error_response.encode('utf-8'))
            
            def do_OPTIONS(self):
                """CORS preflight를 위한 OPTIONS 요청 처리 (브라우저가 실제 요청 전 권한 확인)"""
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', '*')
                self.end_headers()

        # 수정된 handler로 커스텀 뷰어 생성
        class CustomSessionReplayViewer(SessionReplayViewer):
            def start(self):
                """커스텀 handler로 재생 뷰어 서버 시작"""
                # 뷰어 디렉토리가 존재하는지 확인
                self.viewer_path.mkdir(parents=True, exist_ok=True)
                
                # 사용 가능한 포트 찾기
                port = self.find_available_port()
                
                # 요청 handler 생성 (factory pattern)
                def handler_factory(*args, **kwargs):
                    return CustomSessionReplayHandler(self.data_source, self.viewer_path, *args, **kwargs)
                
                # 서버 시작
                self.server = HTTPServer(('', port), handler_factory)
                
                # 스레드에서 시작 (메인 스레드 블로킹 방지)
                server_thread = threading.Thread(target=self.server.serve_forever)
                server_thread.daemon = True  # 메인 프로그램 종료 시 함께 종료
                server_thread.start()
                
                url = f"http://localhost:{port}"
                
                console.print(Panel(
                    f"[bold cyan]Session Replay Viewer Running[/bold cyan]\n\n"
                    f"URL: [link]{url}[/link]\n\n"
                    f"[yellow]Press Ctrl+C to stop[/yellow]",
                    title="Ready",
                    border_style="green"
                ))
                
                # 브라우저 열기
                webbrowser.open(url)
                
                # 종료 처리 (Ctrl+C 시그널 핸들링)
                def signal_handler(sig, frame):
                    console.print("\n[yellow]Shutting down...[/yellow]")
                    self.server.shutdown()
                    if hasattr(self.data_source, 'cleanup'):
                        self.data_source.cleanup()
                    sys.exit(0)
                
                signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C 시그널 등록
                
                # 계속 실행
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
        
        # data source 생성
        data_source = CustomS3DataSource(
            bucket=s3_location['bucket'],
            prefix=s3_location['prefix'],
            session_id=latest_session
        )
        
        print(f"🎬 Starting session replay viewer for: {latest_session}")
        viewer = CustomSessionReplayViewer(data_source=data_source, port=8002)
        viewer.start()  # Ctrl+C까지 블록됨
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """메인 플로우"""
    
    console.print("🚀 Bedrock AgentCore Browser Complete Example")
    console.print("=" * 50)
    
    browser_client = None
    
    try:
        # 1단계: 녹화 기능이 활성화된 browser 생성
        console.print("\n📝 Step 1: Creating browser with recording enabled...")
        browser_client, s3_location = create_browser_with_recording()
        
        # 2단계: 제어 기능이 있는 라이브 뷰어
        console.print("\n👁️  Step 2: Starting live viewer...")
        run_live_viewer_with_control(browser_client)
        
        # 3단계: 녹화가 업로드되도록 세션이 제대로 중지되었는지 확인
        console.print("\n⏹️  Stopping browser session...")
        browser_client.stop()
        console.print("✅ Browser session stopped")
        
        # 4단계: 녹화 보기
        console.print("\n🎬 Step 3: Viewing recordings...")
        view_recordings(s3_location)
        
    except Exception as e:
        console.print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 정리
        if browser_client:
            try:
                browser_client.stop()
                console.print("\n✅ Browser session stopped")
            except:
                pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n🛑 Process interrupted by user")
        sys.exit(0)
