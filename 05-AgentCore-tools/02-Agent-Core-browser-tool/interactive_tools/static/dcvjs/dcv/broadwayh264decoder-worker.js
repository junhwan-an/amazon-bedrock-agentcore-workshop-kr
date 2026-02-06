// Broadway H.264 디코더 라이브러리 로드
self.importScripts(baseUrl + "/lib/broadway/Decoder.js");

// 디코딩 통계 추적 변수
self.frameCount = 0;
self.totalFrameDecodingTime = 0;

// Broadway H.264 디코더 인스턴스 생성
self.broadway = new Decoder;

// 디코딩 완료 시 호출되는 콜백
self.broadway.onPictureDecoded = function(e, a, t) {
    let s;
    // 디코딩된 프레임 데이터를 Uint8Array로 복사 (transferable object로 전송하기 위함)
    s = new Uint8Array(e.length);
    s.set(e, 0, e.length);
    // 메인 스레드로 디코딩된 프레임 전송 (zero-copy transfer)
    self.postMessage({
        type: "frame",
        buffer: s,
        width: a,
        height: t
    }, [s.buffer]);
};

// 메인 스레드로부터 메시지 수신 처리
self.onmessage = function(e) {
    switch (e.data.type) {
        case "frame":
            // 프레임 디코딩 시작 시간 기록
            const a = (new Date).getTime();
            broadway.decode(new Uint8Array(e.data.frame));
            self.frameCount++;
            // 디코딩 소요 시간 누적
            self.totalFrameDecodingTime += (new Date).getTime() - a;
            break;
        case "stats":
            // 디코딩 통계 정보 전송
            self.postMessage({
                type: "stats",
                frameCount: self.frameCount,
                totalFrameDecodingTime: self.totalFrameDecodingTime,
                averageDecodingTime: self.totalFrameDecodingTime / self.frameCount,
                averageDecodingFPS: self.frameCount / (self.totalFrameDecodingTime / 1e3)
            });
            // 통계 초기화
            self.frameCount = 0;
            self.totalFrameDecodingTime = 0;
            break;
        case "close":
            self.postMessage({
                type: "info",
                message: "Closing H264 worker"
            });
            self.close();
    }
};