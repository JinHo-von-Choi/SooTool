# 외부 정책 팩 모델 (일본, EU 등 글로벌 확장)

글로벌 확장(로드맵 C3)은 정확성 검수 인력이 병목이므로, 프로젝트가 모든 국가의 세법을 직접 유지하지 않고 서명된 외부 팩으로
수용하는 구조를 기준으로 한다. 이 문서는 현재 구현으로 가능한 범위와 불가능한 범위, 수용 조건을 정리한다.

## 팩 형식과 명령

팩은 JSON 파일이며 `format`(1), `manifest`(`name`, `version`, `publisher`, 선택 `description`), `bundles`(서명된 정책 번들 목록),
`signature`(manifest 와 번들 해시 목록 전체에 대한 ed25519 서명)를 가진다.

```bash
# 제공자: 번들을 만들고(policy_export, 서명 키는 SOOTOOL_POLICY_KEY_FILE) 팩으로 묶는다
sootool pack build --manifest manifest.json --bundle income.json --bundle gift.json > kr-sample.pack.json

# 받는 쪽: 제공자의 공개 키로 검증한 뒤 설치한다(설치는 관리자 모드, 번들마다 policy_import 의 검증과 감사 기록을 거친다)
sootool pack verify kr-sample.pack.json --public-key <base64>
SOOTOOL_ADMIN_MODE=1 sootool pack install kr-sample.pack.json --public-key <base64>
```

manifest, 번들 내용, 번들 목록 중 무엇이든 바뀌거나 빠지면 팩 서명 검증이 실패하고, 다른 키로 서명된 팩은 거부된다.
구현은 `src/sootool/policy_mgmt/packs.py`, 시험은 `tests/policy_mgmt/test_packs.py`.

## 현재 가능한 것

정책 팩은 기존 도구가 읽는 정책 YAML 의 묶음이다. 이미 구현된 장치로 외부에서 제공받은 팩을 안전하게 들일 수 있다.

1. 정책 문서: 헤더(`effective_date`, `effective_to`, `status`, `notice_no`, `source_url`, `citations`, `reviewed_by`)와 `data`.
   스키마 검증(`sootool.policy_validate`)과 해시(`sha256`) 검증을 통과해야 한다.
2. 번들 서명: 제공자가 `sootool.policy_export` 로 번들을 만들어 ed25519 서명을 붙인다(키는 `SOOTOOL_POLICY_KEY_FILE`).
   받는 쪽은 `sootool.policy_import` 에서 `require_signature=true` 와 제공자의 공개 키(`public_key_b64`)로 검증하거나,
   `SOOTOOL_POLICY_REQUIRE_SIGNATURE=1` 로 서명 없는 가져오기를 막는다.
3. 시점 지정: 가져온 정책은 `as_of` 와 `include_proposed` 로 선택되며, 검수 중인 값은 `status: proposed` 로 두어 기본 계산에서
   제외한다. 응답은 적용된 정책의 출처와 근거 조문(`policy_citations`)을 반환한다.
4. 감사: 가져오기와 활성화는 감사 로그에 기록되고 실행 영수증의 `policy_sha256` 에 정책 해시가 남는다.

## 현재 불가능한 것

- 새 국가의 계산 로직(도구 코드)을 외부에서 들이는 것. 도구 코드는 이 저장소의 모듈이며, 플러그인 진입점(entry points)은
  의도적으로 두지 않았다(검수되지 않은 코드를 서명만으로 실행하게 되기 때문이다). 팩은 기존 도구의 정책 데이터만 교체하거나 추가한다(예: `tax_us` 의 주별 정책 파일).
- 한국 정책 파일이 쓰는 스키마와 다른 구조의 정책. 새 구조는 도구 코드와 스키마(`policy_mgmt/schemas.py`)를 함께 추가해야 한다.

## 수용 조건

일본, EU 도구는 아래가 모두 갖춰진 뒤 추가한다.

1. 팩 제공자(검수 주체)가 있고 공개 키가 프로젝트 문서에 등록되어 있다.
2. 모든 정책 값에 1차 출처(조문, 고시)와 시행일이 붙고 `reviewed_by` 에 검수자가 기록된다.
3. 계산 규칙을 정의하는 도구 코드를 이 저장소에 기여하고, 법령 예시나 공식 계산 예시를 기대값으로 한 시험이 있다.
4. 연 2회 정책 갱신 창구(12월 세법 확정 시점 포함)에서 갱신 책임자가 있다.

조건이 충족되지 않은 국가의 도구는 만들지 않는다. 확인되지 않은 규칙을 그럴듯하게 채우는 것이 가장 큰 위험이기 때문이다.
