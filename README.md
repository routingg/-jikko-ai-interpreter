# 내 손안의 AI 통역사 — I2C LCD 버전

이 패키지는 **I2C 백팩이 붙은 1602 LCD** 기준입니다. 병렬(6선) 배선용 코드는 git 기록(`3e667dc` 이전 커밋)에 남아 있습니다.

## LCD 연결

LCD 백팩의 GND→GND, VCC→5V, SDA→**A4**, SCL→**A5**. 글자가 안 보이면 백팩의 파란 가변저항으로 대비를 조절하세요.

## 실행 순서 (Windows)

0. Arduino IDE 라이브러리 관리자에서 **`LiquidCrystal I2C`**(Frank de Brabander)를 설치합니다. I2C 주소는 스케치가 시작할 때 `0x20~0x3F`에서 자동으로 찾습니다. 주소를 직접 확인하려면 `arduino/i2c_scanner`를 올려 보세요.
1. Arduino IDE에서 `arduino/lcd_interpreter/lcd_interpreter.ino` 열고 **업로드**합니다. LCD에 `AI TRANSLATOR / READY`가 떠야 합니다. **업로드할 때는 서버를 꺼 두세요.** 서버가 COM 포트를 잡고 있으면 업로드가 `액세스 거부`로 실패합니다.
2. Arduino IDE **시리얼 모니터를 닫습니다**. (이미 사용 중인 COM 포트는 Python에서 열 수 없습니다.)
3. `.env.example`을 `.env`로 복사하고 `OPENAI_API_KEY` 와 `ARDUINO_PORT` (예: COM4)를 지정합니다. API 키는 반드시 비공개로 유지하세요. 별도 OpenAI API 과금이 발생할 수 있습니다.
4. `START_WINDOWS.bat`를 실행합니다. 또는 CMD에서 `py -m pip install -r requirements.txt` 후 `py server.py`를 실행합니다.
5. `http://127.0.0.1:8000` 에 접속합니다. 먼저 **LCD 연결 테스트**를 눌러 실제 화면의 `JIKKO SHIELD / LCD IS READY`를 확인하세요.
6. 텍스트로 `안녕하세요`를 입력하고 **영어로 번역하고 LCD 보내기**를 누르세요. 성공하면 GPT 번역 결과가 LCD에 출력됩니다.
7. 그다음 **한국어로 말하기**를 눌러 마이크 권한을 허용하고 말하세요. 음성인식 후 번역 버튼을 눌러야 LCD로 전송됩니다. Chrome/Edge의 음성인식 지원과 네트워크가 필요할 수 있습니다.

## 점검

- LCD에 네모만 나오면: I2C 스케치가 올라갔는지(병렬용 스케치면 네모만 나옵니다), 대비 가변저항, SDA/SCL 배선을 확인하세요. 시리얼로 `LCD at 0x27`이 나오면 LCD를 찾은 것이고 `NO I2C LCD FOUND`면 배선 문제입니다.
- 서버는 켜질 때 `.env`를 읽습니다. `ARDUINO_PORT`를 바꾸면 서버를 재시작하세요. 보드를 바꾸면 COM 번호가 달라질 수 있습니다.
- `could not open port COM3`가 보이면 `.env`의 `ARDUINO_PORT`를 실제 번호로 교체하고 시리얼 모니터를 닫으세요.
- `LCD acknowledgment error`가 보이면 Arduino 통신속도 `9600`과 업로드된 최종 스케치를 확인하세요.
- API 키 오류가 발생하면 OpenAI API 키와 사용 가능한 결제/모델 권한을 확인하세요.
- 실제 보드를 연결하지 않고 화면만 확인할 때는 `DEMO_MODE=1`로 실행할 수 있으나, **실제 GPT 번역/하드웨어 출력이 아님**을 구분해야 합니다.
- 긴 번역문은 16자×2줄 단위로 자동 넘김합니다. 마지막 페이지가 남습니다.
