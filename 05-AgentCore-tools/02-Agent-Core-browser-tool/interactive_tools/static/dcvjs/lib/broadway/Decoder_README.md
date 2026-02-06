# Decoder.js 코드 설명

## 파일 개요
이 파일은 Broadway.js H.264 비디오 디코더의 핵심 구현체입니다. Emscripten을 사용하여 C/C++ 코드를 JavaScript/WebAssembly로 컴파일한 결과물입니다.

## 주요 구조

### 1. 모듈 래퍼 (Module Wrapper)
```javascript
var getModule = function(par_broadwayOnHeadersDecoded, par_broadwayOnPictureDecoded)
```
- **목적**: Broadway 디코더 모듈을 생성하는 팩토리 함수
- **매개변수**:
  - `par_broadwayOnHeadersDecoded`: H.264 헤더 디코딩 완료 시 호출되는 콜백
  - `par_broadwayOnPictureDecoded`: 프레임(픽처) 디코딩 완료 시 호출되는 콜백

### 2. Emscripten 런타임
```javascript
var Module = typeof Module !== "undefined" ? Module : {};
```
- **목적**: Emscripten이 생성한 WebAssembly/asm.js 런타임 환경
- **주요 기능**:
  - 메모리 관리 (HEAP8, HEAP16, HEAP32 등)
  - 함수 호출 인터페이스
  - 파일 시스템 에뮬레이션

### 3. asm.js 코어 (EMSCRIPTEN_START_ASM ~ EMSCRIPTEN_END_ASM)
```javascript
var asm = (function(global, env, buffer) {
  "use asm";
  // ... 최적화된 저수준 코드
})
```
- **목적**: H.264 디코딩 알고리즘의 핵심 구현
- **특징**:
  - asm.js 형식으로 작성되어 브라우저에서 최적화 가능
  - 타입 어노테이션을 통한 성능 최적화
  - 직접 메모리 접근으로 빠른 처리

### 4. 주요 디코딩 함수들

#### `_broadwayInit()`
- H.264 디코더 초기화
- 메모리 할당 및 내부 상태 설정

#### `_broadwayCreateStream(size)`
- 비디오 스트림 버퍼 생성
- 매개변수: 버퍼 크기 (기본 8MB)

#### `_broadwayPlayStream(length)`
- H.264 NAL 유닛 디코딩 실행
- 매개변수: 디코딩할 데이터 길이

### 5. YUV to RGB 변환기
```javascript
var getAsm = function(parWidth, parHeight)
```
- **목적**: YUV 색공간을 RGB로 변환
- **최적화**: asm.js를 사용한 고속 변환
- **캐싱**: 해상도별로 변환기 인스턴스 캐싱

### 6. Decoder 클래스
```javascript
var Decoder = function(parOptions)
```
- **주요 옵션**:
  - `rgb`: RGB 출력 활성화 (기본: YUV)
  - `sliceMode`: 슬라이스 모드 활성화
  - `sliceNum`: 슬라이스 번호
  - `reuseMemory`: 메모리 재사용 최적화

- **주요 메서드**:
  - `decode(typedArray, info)`: H.264 데이터 디코딩
  - `onPictureDecoded(buffer, width, height, infos)`: 디코딩 완료 콜백

### 7. Worker 지원
```javascript
self.addEventListener('message', function(e) {
  // Worker 메시지 처리
})
```
- **목적**: Web Worker에서 디코딩 실행
- **장점**: 메인 스레드 블로킹 방지
- **메시지 타입**:
  - `buf`: 디코딩할 데이터
  - `slice`: 슬라이스 데이터
  - `reuse`: 메모리 재사용

## 핵심 개념

### NAL Unit (Network Abstraction Layer Unit)
- H.264 비디오 스트림의 기본 단위
- 시작 코드: `0x00 0x00 0x00 0x01` 또는 `0x00 0x00 0x01`
- 타입: SPS, PPS, IDR, 일반 프레임 등

### Slice Mode
- 프레임을 여러 슬라이스로 분할하여 병렬 처리
- 여러 Worker에서 동시에 디코딩 가능
- 성능 향상 및 지연 시간 감소

### Memory Management
- `streamBuffer`: 입력 스트림 버퍼 (최대 8MB)
- `pictureBuffers`: 디코딩된 프레임 버퍼
- `HEAP8/16/32`: Emscripten 메모리 힙

## 성능 최적화

### 1. asm.js 사용
- 타입 어노테이션으로 JIT 최적화
- 네이티브에 가까운 성능

### 2. 메모리 재사용
- ArrayBuffer 전송 시 소유권 이전
- 불필요한 복사 최소화

### 3. 캐싱
- YUV-RGB 변환기 캐싱
- 해상도별 인스턴스 재사용

### 4. Worker 활용
- 백그라운드 디코딩
- 메인 스레드 응답성 유지

## 사용 예제

```javascript
// 디코더 생성
var decoder = new Decoder({
  rgb: true,  // RGB 출력
  reuseMemory: true  // 메모리 재사용
});

// 디코딩 완료 콜백 설정
decoder.onPictureDecoded = function(buffer, width, height, infos) {
  // buffer: YUV 또는 RGB 데이터
  // width, height: 프레임 크기
  // infos: 디코딩 정보 (타이밍 등)
  console.log('Frame decoded:', width, 'x', height);
};

// H.264 데이터 디코딩
var h264Data = new Uint8Array([...]); // NAL units
decoder.decode(h264Data, {
  startDecoding: Date.now()
});
```

## 주의사항

1. **메모리 제한**: 스트림 버퍼는 최대 8MB
2. **NAL Unit 형식**: 올바른 시작 코드 필요
3. **Worker 사용 시**: 데이터 전송 오버헤드 고려
4. **브라우저 호환성**: asm.js 지원 브라우저 필요

## 디버깅 팁

1. `console.log`로 디코딩 타이밍 확인
2. `infos` 객체에서 성능 메트릭 확인
3. NAL unit 타입 확인 (SPS, PPS, IDR 등)
4. 메모리 사용량 모니터링

## 참고 자료

- [H.264 스펙](https://www.itu.int/rec/T-REC-H.264)
- [Emscripten 문서](https://emscripten.org/)
- [asm.js 스펙](http://asmjs.org/)
- [Broadway.js GitHub](https://github.com/mbebenita/Broadway)
