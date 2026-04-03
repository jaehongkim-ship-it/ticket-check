---
name: slack-jira-report
description: "Jira 점검 결과를 Slack mrkdwn 형식으로 변환하여 DM 발송. ticket-check 스킬에서 호출됩니다. Slack 메시지 포맷, Jira 리포트 발송, 점검 결과 알림 시 사용하세요."
allowed-tools: mcp__claude_ai_Slack__slack_send_message
---

# Slack Jira 리포트 발송

Jira 점검 결과 데이터를 받아 정확한 Slack mrkdwn 형식으로 변환하고 DM을 발송합니다.

이 스킬의 핵심 역할은 **모든 티켓 번호를 클릭 가능한 Slack 링크로 변환하는 것**입니다. Slack은 마크다운이 아닌 자체 mrkdwn 문법을 사용하므로 형식이 정확해야 합니다.

## 환경 정보

- Jira URL: `https://musinsa-oneteam.atlassian.net`
- Slack User ID: `U0AM4NM1U01`

## 티켓 링크 변환 규칙

모든 `CSE-숫자` 패턴을 Slack mrkdwn 링크로 변환하세요:

```
<https://musinsa-oneteam.atlassian.net/browse/CSE-1041|CSE-1041>
```

텍스트 어디에든 `CSE-1041` 같은 티켓 번호가 나오면 위 형식으로 감싸야 합니다. 예외 없이 모든 곳에 적용하세요. 이유: Slack에서 `<URL|표시텍스트>` 형식만 클릭 가능한 링크로 렌더링됩니다. 플레인 텍스트 티켓 번호는 사용자가 수동으로 찾아가야 해서 불편합니다.

**올바른 예:**
```
<https://musinsa-oneteam.atlassian.net/browse/CSE-1041|CSE-1041> Lambda 기능 테스트 (~2026-04-06)
```

**잘못된 예 (이렇게 하면 안 됨):**
```
CSE-1041 Lambda 기능 테스트 (~2026-04-06)
`CSE-1041` Lambda 기능 테스트
[CSE-1041](https://...) Lambda 기능 테스트
```

## 입력 데이터 형식

호출자(ticket-check)가 다음 구조의 데이터를 전달합니다:

```json
{
  "date": "2026-04-03",
  "total_checked": 11,
  "rounds": 1,
  "auto_fixed": 0,
  "manual_needed": 1,
  "missing_fields": [
    {"key": "CSE-1019", "status": "완료", "fields": ["Actual MD"]}
  ],
  "auto_transitions": [
    {"key": "CSE-XXX", "from": "SUGGESTED", "to": "In Progress"}
  ],
  "active_tickets": [
    {"key": "CSE-1041", "summary": "Lambda 기능 테스트", "due": "2026-04-06"},
    {"key": "CSE-1009", "summary": "AWS Connect IVR Contact Flow 설계", "due": "2026-04-10"}
  ],
  "no_active_warning": false
}
```

## 메시지 조립 규칙

### 문제 없을 때 (missing_fields, auto_transitions 모두 비어 있고 no_active_warning false)

```
[Jira 티켓 점검] 2026-04-03 완료
점검 완료: 11건, 문제없음

*활성 티켓 (6건)*
• <https://musinsa-oneteam.atlassian.net/browse/CSE-1041|CSE-1041> Lambda 기능 테스트 (~2026-04-06)
• <https://musinsa-oneteam.atlassian.net/browse/CSE-1009|CSE-1009> AWS Connect IVR Contact Flow 설계 (~2026-04-10)
```

### 문제 있을 때

```
[Jira 티켓 점검] 2026-04-03 완료

*필수필드 누락*
• <https://musinsa-oneteam.atlassian.net/browse/CSE-1019|CSE-1019> (완료) - Actual MD 누락

*Progress 미비 (자동 수정)*
• <https://musinsa-oneteam.atlassian.net/browse/CSE-XXX|CSE-XXX> SUGGESTED → In Progress

*활성 티켓 (6건)*
• <https://musinsa-oneteam.atlassian.net/browse/CSE-1041|CSE-1041> Lambda 기능 테스트 (~2026-04-06)

점검 11건 | 라운드 1회 | 자동수정 0건 | 수동조치 1건
```

### 활성 티켓 0건 경고

```
[Jira 티켓 점검] 2026-04-03 완료

:warning: *활성 티켓 없음* — 오늘 기준 진행 중인 티켓이 없습니다. 확인이 필요합니다.

점검 11건 | 라운드 1회 | 자동수정 0건 | 수동조치 0건
```

## 발송

slack_send_message 사용:
- channel: `U0AM4NM1U01`
- 메시지는 딱 1건만 발송

## 섹션 포함 규칙

- `missing_fields`가 비어 있으면 "필수필드 누락" 섹션 생략
- `auto_transitions`가 비어 있으면 "Progress 미비" 섹션 생략
- 문제 있을 때만 하단 요약 라인(점검 N건 | ...) 포함
- `active_tickets`가 있으면 항상 "활성 티켓" 섹션 포함
