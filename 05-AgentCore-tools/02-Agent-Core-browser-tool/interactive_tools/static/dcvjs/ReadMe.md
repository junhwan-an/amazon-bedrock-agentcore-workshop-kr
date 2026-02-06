# Amazon DCV Web Client SDK

Amazon DCV Web Client SDK는 자체 Amazon DCV 웹 브라우저 클라이언트 애플리케이션을
개발할 수 있게 해주는 JavaScript 라이브러리입니다.
애플리케이션 사용자는 네이티브 Amazon DCV 세션에 연결하고 상호작용할 수 있습니다.

## 사전 요구사항

Amazon DCV Web Client SDK 작업을 시작하기 전에 Amazon DCV 및 Amazon DCV 세션에
익숙해지도록 하십시오. 자세한 내용은 [Amazon DCV Administrator Guide](https://docs.aws.amazon.com/dcv/latest/adminguide)를 참조하십시오.

Amazon DCV Web Client SDK는 Amazon DCV server 버전 2020 이상을 지원합니다.

## 브라우저 지원

Amazon DCV Web Client SDK는 JavaScript (ES6)를 지원하며 JavaScript 또는
TypeScript 애플리케이션에서 사용할 수 있습니다.

Amazon DCV Web Client SDK는 다음 웹 브라우저를 지원합니다:
 * Google Chrome - 최신 3개 주요 버전
 * Mozilla Firefox - 최신 3개 주요 버전
 * Microsoft Edge - 최신 3개 주요 버전
 * Apple Safari for macOS - 최신 3개 주요 버전

SDK는 최신 브라우저 버전에서 작동하도록 설계되었지만, ES5 코드로 트랜스파일하여
이전 브라우저에서 사용할 수 있습니다. 이 경우 일부 기능이 사용 불가능할 수 있습니다.

## 버전 관리

Amazon DCV Web Client SDK는 시맨틱 버전 관리 모델을 따릅니다.
버전은 다음 형식을 따릅니다: major.minor.patch. 1.x.x에서 2.x.x로의 변경과 같은
주요 버전 변경은 코드 변경 및 계획된 배포가 필요할 수 있는 호환성 파괴 변경을
나타냅니다. 1.1.x에서 1.2.x로의 변경과 같은 마이너 버전 변경은 하위 호환되지만
더 이상 사용되지 않는 요소를 포함할 수 있습니다.

## 라이브러리 사용 방법

SDK 레퍼런스 및 일부 예제는 [공식 문서 웹사이트](https://docs.aws.amazon.com/dcv/latest/websdkguide)에서 확인할 수 있습니다.

## 라이선스

라이선스는 EULA.txt 파일을 참조하십시오.
Third party 고지사항은 third-party-licenses.txt 파일을 참조하십시오.
