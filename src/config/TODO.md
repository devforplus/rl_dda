# 설정 파일 리팩토링 작업 진행 상황

## 완료된 작업
- [x] 기존 const.py에서 모듈화된 설정 파일 구조로 마이그레이션 시작
- [x] 경로 및 색상 팔레트 설정을 config/paths 및 config/colors로 이동
- [x] 스테이지 관련 상수를 config/stage 모듈로 이동
- [x] 음악 관련 설정을 config/music 모듈로 이동
- [x] 사운드 관련 상수 및 열거형을 config/sound 모듈로 이동
- [x] 플레이어 관련 상수를 config/player 데이터클래스로 변환

## 작업 중인 항목
- [ ] render 모듈 구현 중
- [ ] const.py 파일의 나머지 상수 이전 작업 중

## 남은 작업
- [ ] 기존 코드에서 const.py 대신 새로운 설정 모듈 import하도록 수정
- [ ] const.py에서 완전히 마이그레이션 된 상수 제거
- [ ] 각 설정 모듈에 대한 추가 테스트 작성
- [ ] render 모듈 완성 및 테스트 작성

## 참고사항
- 현재 일부 테스트에서 Python 버전 호환성 관련 문제 발생 (typing.List vs list[str])
- config/paths 모듈에서 MUSIC_DIR 추가 필요 