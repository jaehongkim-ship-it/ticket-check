#!/usr/bin/env python3
"""
Slack Jira 리포트 메시지 형식 검증기.

Slack으로 보내기 전에 메시지가 올바른 mrkdwn 형식인지 검사합니다.
주요 검증: 모든 CSE-숫자 티켓 번호가 <URL|CSE-XXX> 형식의 Slack 링크인지 확인.

사용법:
  python validate_message.py "메시지 텍스트"
  python validate_message.py --file message.txt

종료 코드:
  0: 검증 통과
  1: 검증 실패 (수정 필요한 항목 출력)
"""

import re
import sys
import json
import argparse

JIRA_BASE_URL = "https://musinsa-oneteam.atlassian.net/browse"
TICKET_PATTERN = re.compile(r"CSE-\d+")
# <URL|표시텍스트> 안에 있는 티켓 번호 매칭
SLACK_LINK_PATTERN = re.compile(r"<https://musinsa-oneteam\.atlassian\.net/browse/(CSE-\d+)\|CSE-\d+>")


def validate_message(message: str) -> dict:
    """메시지를 검증하고 결과를 반환합니다."""
    errors = []
    warnings = []

    # 1. 모든 티켓 번호 찾기
    all_tickets = set(TICKET_PATTERN.findall(message))

    # 2. 올바른 Slack 링크 안의 티켓 번호 찾기
    linked_tickets = set(SLACK_LINK_PATTERN.findall(message))

    # 3. 링크 없는 플레인 텍스트 티켓 번호 찾기
    # Slack 링크 부분을 제거한 후 남은 텍스트에서 티켓 번호 검색
    text_without_links = SLACK_LINK_PATTERN.sub("__LINKED__", message)
    bare_tickets = set(TICKET_PATTERN.findall(text_without_links))

    for ticket in sorted(bare_tickets):
        errors.append({
            "type": "bare_ticket",
            "ticket": ticket,
            "message": f"{ticket}이 Slack 링크 없이 플레인 텍스트로 사용됨",
            "fix": f"<{JIRA_BASE_URL}/{ticket}|{ticket}>",
        })

    # 4. 마크다운 링크 형식 감지 [CSE-XXX](URL)
    md_links = re.findall(r"\[CSE-\d+\]\(https?://[^)]+\)", message)
    for md_link in md_links:
        ticket = TICKET_PATTERN.search(md_link).group()
        errors.append({
            "type": "markdown_link",
            "ticket": ticket,
            "message": f"마크다운 링크 형식 사용됨: {md_link}",
            "fix": f"<{JIRA_BASE_URL}/{ticket}|{ticket}>",
        })

    # 5. 백틱으로 감싼 티켓 번호 감지 `CSE-XXX`
    backtick_tickets = re.findall(r"`(CSE-\d+)`", message)
    for ticket in backtick_tickets:
        errors.append({
            "type": "backtick_ticket",
            "ticket": ticket,
            "message": f"백틱으로 감싼 티켓 번호: `{ticket}`",
            "fix": f"<{JIRA_BASE_URL}/{ticket}|{ticket}>",
        })

    # 6. 메시지가 비어있는지 확인
    if not message.strip():
        errors.append({
            "type": "empty_message",
            "ticket": None,
            "message": "메시지가 비어있음",
            "fix": None,
        })

    # 7. Slack 링크 형식이 올바른지 (URL과 표시텍스트의 티켓 번호 일치)
    mismatched = re.findall(
        r"<https://musinsa-oneteam\.atlassian\.net/browse/(CSE-\d+)\|(CSE-\d+)>",
        message,
    )
    for url_ticket, display_ticket in mismatched:
        if url_ticket != display_ticket:
            errors.append({
                "type": "mismatched_link",
                "ticket": url_ticket,
                "message": f"URL({url_ticket})과 표시텍스트({display_ticket}) 불일치",
                "fix": f"<{JIRA_BASE_URL}/{url_ticket}|{url_ticket}>",
            })

    # 8. 메시지 건수 확인 (여러 메시지 구분자 감지는 호출자 책임)

    passed = len(errors) == 0

    return {
        "passed": passed,
        "total_tickets": len(all_tickets),
        "linked_tickets": len(linked_tickets),
        "errors": errors,
        "warnings": warnings,
    }


def format_result(result: dict) -> str:
    """검증 결과를 사람이 읽기 쉬운 형태로 포맷합니다."""
    lines = []

    if result["passed"]:
        lines.append(f"PASS: 검증 통과 (티켓 {result['total_tickets']}건, 링크 {result['linked_tickets']}건)")
    else:
        lines.append(f"FAIL: 검증 실패 (오류 {len(result['errors'])}건)")
        lines.append("")
        for i, err in enumerate(result["errors"], 1):
            lines.append(f"  {i}. [{err['type']}] {err['message']}")
            if err["fix"]:
                lines.append(f"     수정: {err['fix']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Slack Jira 리포트 메시지 검증기")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("message", nargs="?", help="검증할 메시지 텍스트")
    group.add_argument("--file", "-f", help="메시지가 담긴 파일 경로")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")

    args = parser.parse_args()

    if args.file:
        with open(args.file, "r") as f:
            message = f.read()
    else:
        message = args.message

    result = validate_message(message)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_result(result))

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
