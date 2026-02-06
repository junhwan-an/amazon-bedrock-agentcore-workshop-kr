#!/usr/bin/env python3
"""
Standalone Session Replay Viewer

This script allows you to view Bedrock Agentcore browser recordings stored in S3
without needing to create a new browser session.

Usage:
    python3 view_recordings.py --bucket BUCKET_NAME --prefix PREFIX [--session SESSION_ID] [--port PORT]

Example:
    python3 view_recordings.py --bucket session-record-test-123456789012 --prefix replay-data

Environment Variables:
    AWS_REGION          - AWS region (default: us-west-2)
    AWS_PROFILE         - AWS profile to use for credentials (optional)
"""

import os
import sys
import time
import json
import uuid
import tempfile
import threading
import webbrowser
import socket
import signal
import shutil
import gzip
import io
import argparse
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

import boto3
from rich.console import Console
from rich.panel import Panel

# Console 생성
console = Console()

# 같은 폴더의 session_replay_viewer에서 직접 import
from session_replay_viewer import SessionReplayViewer, SessionReplayHandler

# import 문제를 피하기 위해 이 스크립트에서 CustomS3DataSource를 직접 정의
class CustomS3DataSource:
    """Custom data source for S3 recordings with known structure"""
    
    def __init__(self, bucket, prefix, session_id):
        self.s3_client = boto3.client('s3')
        self.bucket = bucket
        self.prefix = prefix
        self.session_id = session_id
        self.session_prefix = f"{prefix}/{session_id}"
        # 녹화 파일을 다운로드할 임시 디렉토리 생성
        self.temp_dir = Path(tempfile.mkdtemp(prefix='bedrock_agentcore_replay_'))
        
    def cleanup(self):
        """임시 파일 정리"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def list_recordings(self):
        """녹화 목록을 직접 조회"""
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
        
        # 이벤트 수를 세기 위해 batch 파일 목록 조회
        batch_files = []
        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket,
            Prefix=f"{self.session_prefix}/batch-"
        )
        
        if 'Contents' in response:
            batch_files = [obj['Key'] for obj in response['Contents']]
            print(f"✅ Found {len(batch_files)} batch files")
        
        # 녹화 항목 생성
        timestamp = int(time.time() * 1000)  # milliseconds 단위
        duration = 0
        event_count = 0
        
        # timestamp를 올바르게 파싱
        if 'startTime' in metadata:
            try:
                # ISO 8601 형식 처리 (예: "2026-02-05T08:14:30.954Z")
                if isinstance(metadata['startTime'], str):
                    dt = datetime.fromisoformat(metadata['startTime'].replace('Z', '+00:00'))
                    timestamp = int(dt.timestamp() * 1000)
                else:
                    timestamp = metadata['startTime']
            except Exception as e:
                print(f"⚠️ Error parsing startTime: {e}")
                
        # metadata 구조가 다를 수 있어 여러 필드명 시도
        if 'duration' in metadata:
            duration = metadata['duration']
        elif 'durationMs' in metadata:
            duration = metadata['durationMs']
            
        if 'eventCount' in metadata:
            event_count = metadata['eventCount']
        elif 'totalEvents' in metadata:
            event_count = metadata['totalEvents']
        
        # milliseconds를 초 단위로 변환하여 포맷팅
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
            
            # metadata에 batch 파일 목록이 있으면 사용
            batch_files = []
            if 'batches' in metadata and isinstance(metadata['batches'], list):
                for batch in metadata['batches']:
                    if 'file' in batch:
                        batch_files.append(f"{self.session_prefix}/{batch['file']}")
            
            # metadata에서 batch 파일을 찾지 못한 경우 S3에서 직접 검색
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
                    
                    # gzip으로 압축된 JSON lines 형식 파싱
                    with gzip.GzipFile(fileobj=io.BytesIO(response['Body'].read())) as gz:
                        content = gz.read().decode('utf-8')
                        print(f"Read {len(content)} bytes of content")
                        
                        # 각 줄을 개별 JSON 이벤트로 처리 (JSONL 형식)
                        for line in content.splitlines():
                            if line.strip():
                                try:
                                    event = json.loads(line)
                                    # rrweb 이벤트 필수 필드 검증
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
            
            # 이벤트가 충분하지 않으면 테스트용 샘플 생성
            if len(all_events) < 2:
                print("⚠️ Insufficient events, creating sample events for testing")
                # 기본 메타 이벤트 생성 (type 2: meta)
                all_events = [
                    {"type": 2, "timestamp": timestamp, "data": {"href": "https://example.com", "width": 1280, "height": 720}} 
                    for timestamp in range(int(time.time() * 1000), int(time.time() * 1000) + 10000, 1000)
                ]
                # DOM snapshot 이벤트 추가 (type 4: full snapshot)
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

# 이 스크립트에서 CustomSessionReplayHandler를 직접 정의
class CustomSessionReplayHandler(SessionReplayHandler):
    """Custom HTTP request handler for session replay viewer"""
    
    def serve_recordings_list(self):
        """녹화 목록 반환 - HTML 응답 문제 수정"""
        try:
            recordings = self.data_source.list_recordings()
            response = json.dumps(recordings)
            
            # 반환하는 내용을 확인하기 위한 디버그 출력
            print(f"Serving recordings list: {response[:100]}...")
            
            # JSON 응답을 위한 적절한 HTTP header 설정
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response)))
            # CORS header 추가 (브라우저에서 API 호출 허용)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
            
            # 응답을 bytes로 작성
            self.wfile.write(response.encode('utf-8'))
            
        except Exception as e:
            print(f"❌ Error in serve_recordings_list: {e}")
            import traceback
            traceback.print_exc()
            
            # 에러 발생 시에도 JSON 형식으로 응답 (클라이언트가 파싱 가능하도록)
            error_response = json.dumps({
                "error": str(e),
                "recordings": []
            })
            self.send_response(200)  # 클라이언트가 에러를 처리할 수 있도록 200 사용
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(error_response)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
    
    def download_and_serve_recording(self, recording_id):
        """녹화를 다운로드하고 제공 - HTML 응답 문제 수정"""
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
        """CORS preflight 요청 처리 (브라우저가 실제 요청 전에 보내는 사전 확인)"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

# 이 스크립트에서 CustomSessionReplayViewer를 직접 정의
class CustomSessionReplayViewer(SessionReplayViewer):
    def start(self):
        """커스텀 handler로 replay viewer 서버 시작"""
        # viewer 디렉토리가 존재하는지 확인
        self.viewer_path.mkdir(parents=True, exist_ok=True)
        
        # 사용 가능한 포트 찾기
        port = self.find_available_port()
        
        # CustomSessionReplayHandler를 사용하는 factory 함수
        def handler_factory(*args, **kwargs):
            return CustomSessionReplayHandler(self.data_source, self.viewer_path, *args, **kwargs)
        
        # HTTP 서버 시작
        self.server = HTTPServer(('', port), handler_factory)
        
        # daemon 스레드로 서버 실행 (메인 스레드 종료 시 자동 종료)
        server_thread = threading.Thread(target=self.server.serve_forever)
        server_thread.daemon = True
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
        
        # Ctrl+C 시그널 처리
        def signal_handler(sig, frame):
            console.print("\n[yellow]Shutting down...[/yellow]")
            self.server.shutdown()
            if hasattr(self.data_source, 'cleanup'):
                self.data_source.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # 계속 실행
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

def main():
    parser = argparse.ArgumentParser(description="Standalone Session Replay Viewer")
    parser.add_argument("--bucket", required=True, help="S3 bucket name containing recordings")
    parser.add_argument("--prefix", required=True, help="S3 prefix where recordings are stored")
    parser.add_argument("--session", help="Specific session ID to view (optional)")
    parser.add_argument("--port", type=int, default=8080, help="Port to run the viewer on (default: 8080)")
    parser.add_argument("--profile", help="AWS profile to use (optional)")
    args = parser.parse_args()
    
    # AWS profile 설정
    if args.profile:
        print(f"Using AWS profile: {args.profile}")
        boto3.setup_default_session(profile_name=args.profile)
        
    # S3 client 생성 및 bucket 접근 권한 확인
    s3 = boto3.client('s3')
    
    try:
        # bucket이 존재하고 접근 권한이 있는지 확인
        s3.head_bucket(Bucket=args.bucket)
        print(f"✅ Connected to bucket: {args.bucket}")
    except Exception as e:
        print(f"❌ Error accessing bucket {args.bucket}: {e}")
        sys.exit(1)
    
    # session ID가 지정되지 않은 경우 최신 session 자동 검색
    if not args.session:
        print(f"Finding sessions in s3://{args.bucket}/{args.prefix}/")
        try:
            response = s3.list_objects_v2(
                Bucket=args.bucket,
                Prefix=args.prefix
            )
            
            if 'Contents' not in response:
                print("No objects found in S3 location")
                sys.exit(1)
                
            # metadata.json을 포함하는 session 디렉토리 추출
            session_dirs = set()
            
            for obj in response['Contents']:
                key = obj['Key']
                if 'metadata.json' in key:
                    # 경로에서 session 디렉토리 추출 (prefix/session_id/metadata.json)
                    session_dir = key.split('/')[-2]
                    session_dirs.add(session_dir)
                    print(f"Found session with metadata: {session_dir}")
            
            if not session_dirs:
                print("No session directories with metadata.json found")
                sys.exit(1)
                
            # 최신 session 선택 (정렬 후 마지막 항목)
            session_dirs = sorted(list(session_dirs))
            args.session = session_dirs[-1]
            print(f"Using latest session: {args.session}")
            
        except Exception as e:
            print(f"❌ Error listing sessions: {e}")
            sys.exit(1)
    
    # 특정 session에 대한 data source 생성
    data_source = CustomS3DataSource(
        bucket=args.bucket,
        prefix=args.prefix,
        session_id=args.session
    )
    
    # viewer 시작
    print(f"🎬 Starting session replay viewer for: {args.session}")
    print(f"  Bucket: {args.bucket}")
    print(f"  Prefix: {args.prefix}")
    viewer = CustomSessionReplayViewer(data_source=data_source, port=args.port)
    viewer.start()  # Ctrl+C까지 블록됨

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user")
        sys.exit(0)
