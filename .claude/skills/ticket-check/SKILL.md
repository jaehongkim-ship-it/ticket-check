---
name: ticket-check
description: "Jira 티켓 일일 점검 및 Slack DM 리포트. 티켓 점검, ticket check, 일일 점검, 퇴근 전 점검 요청 시 자동 활성화. 반드시 Agent 도구를 사용하여 서브에이전트에게 점검 작업을 위임해야 합니다. MCP 도구(Atlassian Rovo, Slack)를 직접 호출하지 말고 Agent를 통해 호출하세요."
allowed-tools: Agent
---

# Jira 티켓 일일 점검

내 Jira 티켓을 점검하고, 문제를 자동 수정한 뒤, 결과를 Slack DM으로 보냅니다.

## 2단계 오케스트레이션

이 스킬은 두 개의 Agent를 순차 호출합니다:

1. **Agent 1: Jira 점검** — Jira 티켓을 조회하고 점검/자동수정을 수행하여 결과 데이터를 JSON으로 반환
2. **Agent 2: Slack 리포트** — Agent 1의 결과를 `slack-jira-report` 스킬 형식에 맞춰 Slack DM 발송

이렇게 분리하는 이유: Slack 메시지 포맷팅(특히 티켓 링크)을 전담 스킬이 처리하면 형식 오류가 줄어듭니다.

---

## Agent 1: Jira 점검 에이전트

Agent 도구 호출:
- **description**: `"Jira 티켓 점검"`
- **prompt**: 아래 내용 전달

### 프롬프트

```
Jira 티켓을 점검하고 결과를 JSON으로 반환하세요. Slack 메시지는 보내지 마세요.

## 환경 정보
- Cloud ID: 23c14e7d-74ed-40b6-a0bb-fbc1f6351b84
- Jira URL: https://musinsa-oneteam.atlassian.net

## 필드 매핑
| 필드명 | 필드 ID |
|--------|---------|
| Start date | customfield_10015 |
| Due date | duedate |
| Parent | parent |
| Estimate MD | customfield_12766 |
| Actual MD | customfield_12767 |
| Sprint | customfield_10020 |

## 수렴 루프

round = 0
do {
  round++
  changes_made = 0
  1. JQL 재조회: assignee=currentUser() ORDER BY status ASC, updated DESC
  2. 점검 수행
  3. 자동 수정
  4. changes_made += 수정건수
} while (changes_made > 0 AND round < 5)

## 티켓 조회
searchJiraIssuesUsingJql 사용:
- cloudId: 23c14e7d-74ed-40b6-a0bb-fbc1f6351b84
- jql: assignee = currentUser() ORDER BY status ASC, updated DESC
- fields: ["summary", "status", "issuetype", "parent", "customfield_10015", "duedate", "customfield_12766", "customfield_12767", "customfield_10020"]
- maxResults: 50

매 라운드마다 반드시 다시 조회하세요.

## 점검 항목

### 필수필드 누락
모든 티켓 (Done 포함): start date, due date, parent
In Progress / In Code Review / In Developer Test: + Estimate MD
Done(완료): + Actual MD

### Progress 미비
시작일 <= 오늘 AND 상태 SUGGESTED → transitionJiraIssue로 transitionId:"21" 사용해 In Progress 전환
→ changes_made 증가

### 티켓 공백
활성 티켓 (statusCategory != Done, start <= today, due >= today) 0건이면 경고

## 자동 수정 범위
- SUGGESTED → In Progress: O (transition ID "21")
- Estimate MD / Actual MD: X (절대 임의값 금지, 누락 보고만)
- start date / due date: X (누락 보고만)

## 반환 형식

점검 완료 후 반드시 아래 JSON 형식으로 결과를 텍스트로 출력하세요:

{
  "date": "YYYY-MM-DD",
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
    {"key": "CSE-1041", "summary": "Lambda 기능 테스트", "due": "2026-04-06"}
  ],
  "no_active_warning": false
}

Done 티켓 중 필수필드 모두 채워져 있으면 missing_fields에서 제외.
missing_fields, auto_transitions가 없으면 빈 배열 [].
```

### Agent 1 결과 처리

Agent 1이 반환한 JSON을 파싱하여 Agent 2에 전달합니다.

---

## Agent 2: Slack 리포트 에이전트

Agent 도구 호출:
- **description**: `"Slack Jira 리포트 발송"`
- **prompt**: 아래 내용에 Agent 1의 JSON 결과를 포함하여 전달

### 프롬프트 템플릿

```
아래 Jira 점검 결과를 Slack DM으로 발송하세요.

## 점검 결과 데이터
{Agent 1에서 받은 JSON을 여기에 삽입}

## 발송 규칙

slack_send_message 사용:
- channel: U0AM4NM1U01

### 티켓 링크 형식 (절대 규칙)
모든 티켓 번호(CSE-숫자)는 반드시 이 형식으로 작성:
<https://musinsa-oneteam.atlassian.net/browse/CSE-XXX|CSE-XXX>

올바른 예: <https://musinsa-oneteam.atlassian.net/browse/CSE-1041|CSE-1041>
잘못된 예: CSE-1041 (플레인 텍스트), [CSE-1041](URL) (마크다운)

### 메시지 포맷 — 문제 없을 때 (missing_fields, auto_transitions 모두 비어있고 no_active_warning false)

[Jira 티켓 점검] {date} 완료
점검 완료: {total_checked}건, 문제없음

*활성 티켓 ({N}건)*
• <https://musinsa-oneteam.atlassian.net/browse/{key}|{key}> {summary} (~{due})

### 메시지 포맷 — 문제 있을 때

[Jira 티켓 점검] {date} 완료

*필수필드 누락*
• <https://musinsa-oneteam.atlassian.net/browse/{key}|{key}> ({status}) - {fields} 누락

*Progress 미비 (자동 수정)*
• <https://musinsa-oneteam.atlassian.net/browse/{key}|{key}> {from} → {to}

*활성 티켓 ({N}건)*
• <https://musinsa-oneteam.atlassian.net/browse/{key}|{key}> {summary} (~{due})

점검 {total_checked}건 | 라운드 {rounds}회 | 자동수정 {auto_fixed}건 | 수동조치 {manual_needed}건

### 섹션 규칙
- missing_fields 비어있으면 "필수필드 누락" 섹션 생략
- auto_transitions 비어있으면 "Progress 미비" 섹션 생략
- 문제 있을 때만 하단 요약 라인 포함
- 메시지는 딱 1건만 발송

### 발송 전 검증 (필수)
메시지를 조립한 뒤 발송 전에 반드시 검증 스크립트를 실행하세요:
1. 메시지를 /tmp/slack_message.txt에 저장
2. python3 .claude/skills/slack-jira-report/scripts/validate_message.py --file /tmp/slack_message.txt 실행
3. 종료코드 0이면 → slack_send_message로 발송
4. 종료코드 1이면 → 오류를 읽고 메시지 수정 후 재검증 (최대 3회)
5. 발송 완료 후 rm /tmp/slack_message.txt로 임시 파일 삭제
```

---

## 에러 처리

- MCP 도구를 찾을 수 없으면 30초 대기 후 재시도 (최대 3회)
- 개별 티켓 점검 실패 시 해당 티켓 건너뛰고 에러를 리포트에 포함
- Slack 발송 실패 시 콘솔에 리포트 출력

## 주의사항

- Actual MD, Estimate MD는 절대 임의값 금지 — 누락 보고만
- 매 라운드마다 JQL로 최신 데이터 재조회
