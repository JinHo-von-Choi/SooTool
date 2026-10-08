# 보안 정책

## 취약점 제보

보안 취약점은 공개 이슈로 올리지 말고 아래로 비공개 제보한다.

- GitHub Security Advisories: https://github.com/JinHo-von-Choi/SooTool/security/advisories/new
- 이메일: wnpfjfss007@gmail.com

다음을 함께 보내 주면 확인이 빠르다.

- 취약점 설명과 재현 절차
- 영향받는 버전
- 개념 증명 코드나 화면(가능한 경우)

접수 후 7일 안에 답하고, 90일 안에 수정 배포와 공개를 목표로 한다.

## 지원 버전

|버전|보안 수정|
|-|-|
|최신 릴리스|지원|
|직전 minor|중대한 취약점만 백포트|
|그 이전|지원하지 않음|

## 배포 파일 검증

PyPI에 올라간 wheel과 sdist에는 GitHub 빌드 출처 증명(Sigstore 기반 attestation)이 붙는다. 설치 전에 GitHub CLI로 확인할 수 있다.

```bash
pip download sootool==<버전> --no-deps -d dist/
gh attestation verify dist/sootool-<버전>-py3-none-any.whl --repo JinHo-von-Choi/SooTool
```

검증에 성공하면 그 파일을 빌드한 워크플로 실행 정보가 출력된다. 검증에 실패한 파일은 쓰지 않는다. 릴리스별 증명 기록은 https://github.com/JinHo-von-Choi/SooTool/attestations 에서도 볼 수 있다.

## 운영 시 보안 기본값

|항목|기본 동작|
|-|-|
|네트워크 바인딩|`127.0.0.1`. 다른 주소로 열려면 Bearer 토큰(`--auth-token`)이 있어야 기동한다.|
|정책 쓰기 도구|stdio와 Unix 소켓에서만 노출. HTTP로 열려면 `--admin --remote-admin --admin-token`이 모두 필요하다.|
|Unix 소켓|파일 권한 0600|
|`core.calc` 수식|`eval`을 쓰지 않고 허용 목록에 있는 연산과 함수만 해석한다. 노드 수와 길이에 상한이 있다.|
|입력 크기|문자열 길이, 원소 수, 중첩 깊이에 한도가 있어 계산 전에 거부한다.|
|서명 키|정책 번들 키(`SOOTOOL_POLICY_KEY_FILE`), 영수증 키(`SOOTOOL_RECEIPT_KEY_FILE`)는 파일 경로로만 받고 도구 인자로 받지 않는다.|
|정책 파일|`yaml.SafeLoader`로만 읽고, 쓰기는 원자적 교체와 감사 로그를 거친다.|
