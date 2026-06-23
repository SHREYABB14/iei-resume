from typing import List


def parse_list_section(text: str) -> List[str]:
    if not text:
        return []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    items = []
    cur = ''
    for l in lines:
        # treat numbered/bulleted lines as new items
        if l.lstrip().startswith(('-', '*')) or l[0:2].strip().isdigit() or l[0].isdigit():
            if cur:
                items.append(cur.strip())
            cur = l
        else:
            if cur:
                cur += ' ' + l
            else:
                items.append(l)
    if cur:
        items.append(cur.strip())
    return items


def parse_patents(text: str) -> List[str]:
    return parse_list_section(text)


def parse_awards(text: str) -> List[str]:
    return parse_list_section(text)


def parse_memberships(text: str) -> List[str]:
    return parse_list_section(text)
