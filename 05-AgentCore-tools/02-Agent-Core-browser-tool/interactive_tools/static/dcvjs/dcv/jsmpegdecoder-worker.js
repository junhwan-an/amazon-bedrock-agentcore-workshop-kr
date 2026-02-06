// JSMpeg 라이브러리 로드
self.importScripts(baseUrl+"/lib/jsmpeg/jsmpeg.min.js");

// 프레임 디코딩 통계 변수
self.frameCount=0;
self.totalFrameDecodingTime=0;

// MPEG1 비디오 디코더 초기화
self.decoder=new JSMpeg.Decoder.MPEG1Video({});

// 커스텀 렌더러 연결 (YUV 평면을 메인 스레드로 전송)
self.decoder.connect(new class{
    resize(e,t){
        this.width=e;
        this.height=t;
    }
    render(e,t,s){
        // YUV 평면을 하나의 버퍼로 결합 (Y, U, V 순서)
        let a=new Uint8Array(e.byteLength+t.byteLength+s.byteLength);
        a.set(e);
        a.set(s,e.byteLength);
        a.set(t,e.byteLength+t.byteLength);
        // transferable object로 전송하여 복사 비용 절감
        self.postMessage({type:"frame",buffer:a,width:this.width,height:this.height},[a.buffer]);
    }
});

// 메인 스레드로부터 메시지 수신 처리
self.onmessage=function(e){
    switch(e.data.type){
        case"frame":
            const t=(new Date).getTime();
            self.decoder.write(0,new Uint8Array(e.data.frame));
            self.decoder.decode();
            self.frameCount++;
            self.totalFrameDecodingTime+=(new Date).getTime()-t;
            break;
        case"stats":
            // 디코딩 성능 통계 전송
            postMessage({
                type:"stats",
                frameCount:self.frameCount,
                totalFrameDecodingTime:self.totalFrameDecodingTime,
                averageDecodingTime:self.totalFrameDecodingTime/self.frameCount,
                averageDecodingFPS:self.frameCount/(self.totalFrameDecodingTime/1e3)
            });
            self.frameCount=0;
            self.totalFrameDecodingTime=0;
            break;
        case"close":
            self.postMessage({type:"info",message:"Closing MPEG1 worker"});
            self.close();
    }
};