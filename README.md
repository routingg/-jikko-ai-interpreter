# 내 손안의 AI 통역사 — 실제 성공한 LCD 병렬 배선 버전

이 패키지는 **LCD 핀 설정 `LiquidCrystal lcd(7,8,9,10,11,12)`** 기준입니다. I2C용 프로그램이 아닙니다. 이미 성공한 배선을 유지하세요.

## LCD 연결(배선 변경하지 마세요)

LCD RS→D7, E→D8, D4→D9, D5→D10, D6→D11, D7→D12, R/W→GND, VSS→GND, VDD→5V, VO는 현재 성공한 대비 연결 유지. A/K는 적절한 전류 제한 및 전원 연결을 유지하세요. LCD 7~10번 데이터 핀은 미사용입니다.

## 실행 순서 (Windows)

1. Arduino IDE에서 `arduino/lcd_interpreter/lcd_interpreter.ino` 열고 **업로드**합니다. LCD에 `AI TRANSLATOR / READY`가 떠야 합니다.
2. Arduino IDE **시리얼 모니터를 닫습니다**. (이미 사용 중인 COM 포트는 Python에서 열 수 없습니다.)
3. `.env.example`을 `.env`로 복사하고 `OPENAI_API_KEY` 와 `ARDUINO_PORT` (예: COM4)를 지정합니다. API 키는 반드시 비공개로 유지하세요. 별도 OpenAI API 과금이 발생할 수 있습니다.
4. `START_WINDOWS.bat`를 실행합니다. 또는 CMD에서 `py -m pip install -r requirements.txt` 후 `py server.py`를 실행합니다.
5. `http://127.0.0.1:8000` 에 접속합니다. 먼저 **LCD 연결 테스트**를 눌러 실제 화면의 `JIKKO SHIELD / LCD IS READY`를 확인하세요.
6. 텍스트로 `안녕하세요`를 입력하고 **영어로 번역하고 LCD 보내기**를 누르세요. 성공하면 GPT 번역 결과가 LCD에 출력됩니다.
7. 그다음 **한국어로 말하기**를 눌러 마이크 권한을 허용하고 말하세요. 음성인식 후 번역 버튼을 눌러야 LCD로 전송됩니다. Chrome/Edge의 음성인식 지원과 네트워크가 필요할 수 있습니다.

## 점검

- LCD에 네모만 나오면: 과거에 성공한 LCD 문자 출력 코드로 되돌려 배선/전원/대비를 재검증하세요.
- `could not open port COM3`가 보이면 `.env`의 `ARDUINO_PORT`를 실제 번호로 교체하고 시리얼 모니터를 닫으세요.
- `LCD acknowledgment error`가 보이면 Arduino 통신속도 `9600`과 업로드된 최종 스케치를 확인하세요.
- API 키 오류가 발생하면 OpenAI API 키와 사용 가능한 결제/모델 권한을 확인하세요.
- 실제 보드를 연결하지 않고 화면만 확인할 때는 `DEMO_MODE=1`로 실행할 수 있으나, **실제 GPT 번역/하드웨어 출력이 아님**을 구분해야 합니다.
- 긴 번역문은 16자×2줄 단위로 자동 넘김합니다. 마지막 페이지가 남습니다.
