# 보안 정책

작성자: 최진호
작성일: 2026-04-24

---

## 취약점 보고

SooTool에서 보안 취약점을 발견한 경우 공개 이슈로 등록하지 말고 아래 경로로 비공개 제보한다.

- GitHub Security Advisories: https://github.com/JinHo-von-Choi/SooTool/security/advisories/new
- 이메일: wnpfjfss007@gmail.com

제보 시 포함할 정보:
- 취약점 설명 및 재현 절차
- 영향받는 버전
- 개념 증명(PoC) 코드 또는 스크린샷 (가능한 경우)

확인 후 7일 이내 응답하며, 90일 이내 패치 및 공개 공시를 목표로 한다.

---

## 공급망 신뢰 검증

SooTool 0.1.2 이후 모든 릴리스 wheel과 sdist는 GitHub Attestations(Sigstore 기반
build provenance)로 서명된다. 설치 전 다음 방법으로 서명을 검증할 수 있다.

### GitHub CLI로 검증 (권장)

```
gh attestation verify ./sootool-<version>-py3-none-any.whl \
  --repo JinHo-von-Choi/SooTool
```

성공 시 `Attestation verified` 메시지와 함께 빌드 워크플로우 런 URL이 출력된다.
검증 실패 시 해당 파일을 사용하지 않는다.

GitHub CLI 설치: https://cli.github.com/

### Sigstore CLI로 검증 (sigstore.bundle 파일 사용 시)

GitHub Release 페이지에 `.sigstore.bundle` 파일이 함께 첨부된다.

```
pip install sigstore
sigstore verify identity \
  ./sootool-<version>-py3-none-any.whl \
  --bundle ./sootool-<version>-py3-none-any.whl.sigstore.bundle \
  --cert-identity https://github.com/JinHo-von-Choi/SooTool/.github/workflows/publish-pypi.yml@refs/tags/<tag> \
  --cert-oidc-issuer https://token.actions.githubusercontent.com
```

### GitHub Attestations 페이지에서 확인

https://github.com/JinHo-von-Choi/SooTool/attestations

위 페이지에서 각 릴리스의 빌드 provenance 레코드와 서명 주체(Fulcio 인증서)를 확인할 수 있다.

---

## 지원 버전

| 버전 | 보안 지원 여부 |
|-|-|
| 최신 stable | 지원 |
| 이전 minor | 중요 취약점만 백포트 |
| EOL | 미지원 |
