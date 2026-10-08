# 외부 정책 팩

정책 팩은 서명된 정책 번들 여러 개를 하나의 JSON 파일로 묶은 것이다. 다른 조직이 검수한 정책 값을 서명째로 받아 설치할 때 쓴다. 팩은 기존 도구가 읽는 정책 데이터만 담으며 계산 코드는 담지 않는다.

```
제공자                                              받는 쪽
policy_export ─▶ 번들(서명) ─┐
policy_export ─▶ 번들(서명) ─┼─▶ sootool pack build ─▶ 팩(서명) ─▶ pack verify ─▶ pack install
                             │                                     (공개 키)      (관리자 모드,
manifest(name, version, ...) ┘                                                    번들마다 policy_import)
```

## 팩 형식

|필드|내용|
|-|-|
|`format`|형식 버전. 현재 `1`|
|`manifest`|`name`, `version`, `publisher`, 선택 `description`|
|`bundles`|`policy_export`로 만든 서명된 정책 번들 목록|
|`signature`|manifest와 번들 해시 목록 전체에 대한 ed25519 서명|

## 명령

```bash
# 제공자: 번들을 만들고(서명 키는 SOOTOOL_POLICY_KEY_FILE) 팩으로 묶는다
sootool pack build --manifest manifest.json --bundle income.json --bundle gift.json > kr-sample.pack.json

# 받는 쪽: 제공자의 공개 키로 검증하고 설치한다
sootool pack verify kr-sample.pack.json --public-key <base64>
SOOTOOL_ADMIN_MODE=1 sootool pack install kr-sample.pack.json --public-key <base64>
```

manifest, 번들 내용, 번들 목록 중 하나라도 바뀌거나 빠지면 검증이 실패한다. 다른 키로 서명한 팩도 거부한다. 설치는 번들마다 `policy_import`를 거치므로 정책 검증 6단계와 감사 기록이 그대로 적용된다.

## 설치된 정책의 동작

- 정책 파일의 헤더(`effective_date`, `effective_to`, `status`, `citations`, `reviewed_by`)와 해시 검증을 통과해야 한다.
- 계산 시에는 `as_of`와 `include_proposed`로 버전이 선택된다. 검수 중인 값은 `status: proposed`로 두면 기본 계산에서 빠진다.
- 응답에는 적용한 정책의 근거 조문(`policy_citations`)이 붙고, 영수증의 `policy_sha256`에 정책 해시가 남는다.
- 서명 없는 번들을 아예 받지 않으려면 `SOOTOOL_POLICY_REQUIRE_SIGNATURE=1`을 설정한다.

## 할 수 없는 것

- **새 계산 로직 추가.** 팩은 기존 도구의 정책 데이터만 바꾸거나 더한다(예: `tax_us`의 주별 세율 파일). 검수되지 않은 코드를 서명만 믿고 실행하게 되므로 외부 코드를 불러오는 플러그인 진입점은 두지 않는다.
- **새 구조의 정책.** 기존 스키마와 다른 구조는 도구 코드와 스키마(`policy_mgmt/schemas.py`)를 이 저장소에 함께 추가해야 한다.

## 새 국가 도구를 받는 조건

일본, EU 등 새 국가의 세금 도구는 다음이 모두 갖춰졌을 때 추가한다.

1. 정책 팩을 제공하고 검수할 주체가 있고, 그 공개 키가 이 저장소 문서에 등록되어 있다.
2. 모든 정책 값에 1차 출처(조문, 고시)와 시행일이 있고 `reviewed_by`에 검수자가 적혀 있다.
3. 계산 규칙을 구현한 도구 코드가 이 저장소에 기여되고, 법령 예시나 공식 계산 예시를 기대값으로 한 시험이 있다.
4. 매년 세법 확정 시기를 포함해 연 2회 정책을 갱신할 책임자가 있다.

확인되지 않은 규칙을 그럴듯하게 채운 계산기는 틀린 답을 정확해 보이게 만든다. 조건을 갖추지 못한 국가의 도구는 만들지 않는다.
