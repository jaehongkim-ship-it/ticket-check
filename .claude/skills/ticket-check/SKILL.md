---
name: ticket-check
description: "Jira 티켓 일일 점검 및 Slack DM 리포트. 티켓 점검, ticket check, 일일 점검, 퇴근 전 점검 요청 시 자동 활성화."
license: MIT
author: jaehong.kim
allowed-tools: Agent
metadata:
  version: "1.0.0"
  complexity: 0.7
  scope: project
  tags:
    - jira
    - slack
    - automation
    - ticket-check
  agentic_patterns:
    - Plan-Then-Execute
    - Continuous-Autonomous-Task-Loop
  dependencies:
    - type: mcp
      name: Atlassian Rovo
      required: true
      tools: [searchJiraIssuesUsingJql, transitionJiraIssue, getJiraIssue, editJiraIssue]
    - type: mcp
      name: Slack
      required: true
      tools: [slack_send_message]
  examples:
    - trigger: "/ticket-check"
    - trigger: "티켓 점검해줘"
    - trigger: "퇴근 전 점검"
---

# Jira 티켓 일일 점검

내 Jira 티켓을 점검하고, 문제를 자동 수정한 뒤, 결과를 Slack DM으로 보냅니다.

## 환경 정보

- Cloud ID: `23c14e7d-74ed-40b6-a0bb-fbc1f6351b84`
- 프로젝트: CSE (CS 엔지니어링)
- Jira URL: `https://musinsa-oneteam.atlassian.net`
- Slack User ID: `U0AM4NM1U01`

## 필드 매핑

| 필드명 | 필드 ID |
|--------|---------|
| Start date | `customfield_10015` |
| Due date | `duedate` |
| Parent | `parent` |
| Estimate MD | `customfield_12766` |
| Actual MD | `customfield_12767` |
| Sprint | `customfield_10020` |

## 워크플로우: 수렴 루프

상태 전환 시 필수필드 조건이 바뀌므로 변경이 없을 때까지 반복합니다.

```
round = 0
do {
  round++
  changes_made = 0
  1. 전체 내 티켓 JQL 재조회 (최신 상태)
  2. 점검 수행
  3. 자동 수정
  4. changes_made += 수정 건수
} while (changes_made > 0 AND round < 5)
5. Slack DM 발송
```

### Phase 1: 티켓 조회

searchJiraIssuesUsingJql 사용:
- cloudId: `23c14e7d-74ed-40b6-a0bb-fbc1f6351b84`
- jql: `assignee = currentUser() ORDER BY status ASC, updated DESC`
- fields: `["summary", "status", "issuetype", "parent", "customfield_10015", "duedate", "customfield_12766", "customfield_12767", "customfield_10020"]`
- maxResults: 50

**매 라운드마다 반드시 다시 조회하세요.**

### Phase 2: 점검

#### 2-1. 필수필드 누락

모든 티켓 (Done 포함):
- `customfield_10015` (Start date) 누락
- `duedate` (Due date) 누락
- `parent` (상위 항목) 누락

In Progress / In Code Review / In Developer Test 상태:
- `customfield_12766` (Estimate MD) 누락

Done(완료) 상태:
- `customfield_12767` (Actual MD) 누락

#### 2-2. Progress 미비

시작일(`customfield_10015`)이 오늘 또는 과거인데 상태가 **SUGGESTED**인 티켓:
→ transitionJiraIssue로 transition ID `"21"` 사용해 In Progress로 전환
→ `changes_made` 증가

#### 2-3. 티켓 공백

오늘 기준 활성 티켓 (statusCategory != Done, start <= today, due >= today)이 0건이면 경고.

### Phase 3: 자동 수정 범위

| 항목 | 자동 수정 | 비고 |
|------|-----------|------|
| SUGGESTED → In Progress | O | transition ID `"21"` |
| Estimate MD / Actual MD | **X** | 절대 임의값 금지, 누락 보고만 |
| start date / due date | **X** | 누락 보고만 |

### Phase 4: Slack DM 리포트

slack_send_message 사용:
- channel: `U0AM4NM1U01`

**티켓 링크 필수 포함!**
형식: `<https://musinsa-oneteam.atlassian.net/browse/CSE-XXX|CSE-XXX>`

#### 문제 있을 때:

```
*Jira 티켓 일일 점검 리포트*

*필수필드 누락*
• <URL|CSE-XXX> (In Progress) - Estimate MD 누락

*Progress 미비 (자동 수정)*
• <URL|CSE-XXX> SUGGESTED → In Progress

*활성 티켓 (N건)*
• <URL|CSE-1009> AWS Connect IVR Contact Flow...
• <URL|CSE-1006> Lambda: cs-connect-member-lookup...

점검 N건 | 라운드 N회 | 자동수정 N건 | 수동조치 N건
```

#### 문제 없을 때:

```
*Jira 티켓 일일 점검 리포트*
점검 완료: 전체 N건, 문제 없음

*활성 티켓 (N건)*
• <URL|CSE-1009> AWS Connect IVR Contact Flow...
• <URL|CSE-1006> Lambda: cs-connect-member-lookup...
```

## 에러 처리

- MCP 도구를 찾을 수 없으면 30초 대기 후 재시도 (최대 3회)
- 개별 티켓 점검 실패 시 해당 티켓 건너뛰고 에러를 리포트에 포함
- Slack 발송 실패 시 콘솔에 리포트 출력

## 주의사항

- Done 티켓 중 필수필드 모두 채워져 있으면 리포트에서 제외
- Actual MD, Estimate MD는 **절대 임의값 금지** — 누락 보고만
- 매 라운드마다 JQL로 최신 데이터 재조회

---

**Version**: 1.0.0 | **Last Updated**: 2026-04-03
