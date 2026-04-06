# Jira 티켓 점검 자동화

매일 18:20 KST에 내 Jira 티켓을 자동 점검하고 필요한 수정을 수행하는 프로젝트.

## 환경 정보

- Jira Site: musinsa-oneteam.atlassian.net
- Cloud ID: `23c14e7d-74ed-40b6-a0bb-fbc1f6351b84`
- 프로젝트: CSE (CS 엔지니어링)
- 사용자: 김재홍 (jaehong.kim@musinsa.com)
- Account ID: `712020:cbcf14c6-6d14-4a18-b16d-703e0bc0a3b0`

## 스케줄 트리거

- Trigger ID: `trig_01T3J8SDKYQcKsNU7LodsBzJ`
- 스케줄: 평일 18:01 KST (`1 9 * * 1-5` UTC)
- MCP: Atlassian Rovo + Slack
- 알림: Slack DM (User ID: `U0AM4NM1U01`)
- 관리: https://claude.ai/code/scheduled/trig_01T3J8SDKYQcKsNU7LodsBzJ

## Jira 필드 매핑

| 필드명 | 필드 ID | 비고 |
|--------|---------|------|
| Start date | `customfield_10015` | 필수 |
| Due date | `duedate` | 필수 |
| Parent(상위 항목) | `parent` | 필수 |
| Estimate MD | `customfield_12766` | In Progress 필수 |
| Actual MD | `customfield_12767` | Done 필수 |
| Sprint | `customfield_10020` | |
| Done Date | `customfield_10622` | |
| Actual Start Date | `customfield_10624` | |
| AI Contribution (%) | `customfield_12647` | |
| AI Assistant | `customfield_12661` | |
| QA담당자 | `customfield_10290` | |
| Git Repository Name | `customfield_15043` | |
| Story point estimate | `customfield_10016` | Estimate MD와 별개 필드 |
| Story Points | `customfield_10036` | |

## 상태 전환 (Dev/Task 이슈 타입)

| 전환 이름 | 전환 ID | 목표 상태 | 비고 |
|-----------|---------|-----------|------|
| Start | `21` | In Progress | SUGGESTED에서만 가능 |
| In Code Review | `3` | In Code Review | |
| Begin Developer Test | `2` | In Developer Test | |
| Request Review | `4` | In Code Review | |
| Done | `61` | 완료 | hasScreen: true |
| HOLD | `31` | HOLD | |
| Backlog | `11` | Backlog | |
| Open | `71` | SUGGESTED | |

## 점검 방식: 수렴 루프

상태 전환 시 필수필드 조건이 바뀌므로, **1회 점검으로 끝내지 않고 변경이 없을 때까지 반복**합니다.

```
round = 0
do {
  round++
  changes_made = 0

  1. 전체 내 티켓 JQL 재조회 (최신 상태 반영)
  2. 점검 수행 (필수필드 누락, Progress 미비, 티켓 공백)
  3. 자동 수정 (SUGGESTED→In Progress 등)
  4. changes_made += 수정 건수

} while (changes_made > 0 AND round < 5)

5. 최종 리포트 출력
```

예시 흐름:
- Round 1: SUGGESTED 티켓을 In Progress로 전환
- Round 2: 새로 In Progress가 된 티켓의 Estimate MD 누락 발견 → 보고
- Round 3: 추가 변경 없음 → 루프 종료

## 점검 항목

### 1. 필수필드 누락
- 모든 티켓: start date, due date, parent
- In Progress 상태: + Estimate MD
- Done 상태: + Actual MD

### 2. Progress 미비
- 시작일이 오늘 이전인데 SUGGESTED 상태인 티켓 → In Progress로 자동 전환 (transition ID: 21)
- 전환하면 changes_made 증가 → 다음 라운드에서 새 필수필드 재점검

### 3. 티켓 공백
- 오늘 기준 활성 티켓(statusCategory != Done, start <= today, due >= today)이 0건이면 경고

## 자동 수정 범위

| 항목 | 자동 수정 | 비고 |
|------|-----------|------|
| SUGGESTED → In Progress 전환 | O | transition ID 21 |
| Estimate MD / Actual MD 입력 | X | 사용자만 판단 가능, 누락 보고만 |
| start date / due date 입력 | X | 누락 보고만 |
| parent 설정 | X | 누락 보고만 |

## 티켓 범위

- 내게 할당된 전체 티켓 (assignee = currentUser())
- Done 상태 티켓 중 모든 필수필드가 채워져 있으면 리포트에서 제외
