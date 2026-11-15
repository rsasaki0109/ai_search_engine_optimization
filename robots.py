"""robots.txt group selection and path matching, without network side effects.
Supports merged exact product-token groups, wildcard fallback, longest-match
rules, Allow tie-breaking, * and terminal $. Does not simulate bot HTTP access.
"""
from urllib.parse import quote, urlsplit

UNRESERVED = frozenset('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~')


def normalize_path(value):
    out = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == '%' and index + 2 < len(value):
            try:
                octet = int(value[index + 1:index + 3], 16)
                decoded = chr(octet)
                out.append(decoded if decoded in UNRESERVED else f'%{octet:02X}')
                index += 3
                continue
            except ValueError:
                pass
        out.append(quote(char, safe='') if ord(char) > 127 else char)
        index += 1
    return ''.join(out)


def matches(pattern, path):
    """Literal segments avoid backtracking on untrusted wildcard patterns."""
    anchored = pattern.endswith('$')
    if anchored: pattern = pattern[:-1]
    parts = pattern.split('*')
    if not path.startswith(parts[0]): return False
    cursor = len(parts[0])
    if len(parts) == 1: return not anchored or cursor == len(path)
    for part in parts[1:-1]:
        position = path.find(part, cursor)
        if position < 0: return False
        cursor = position + len(part)
    last = parts[-1]
    if anchored:
        return path.endswith(last) and len(path) - len(last) >= cursor
    return path.find(last, cursor) >= 0


def specificity(pattern):
    count, index = 0, 0
    pattern = pattern[:-1] if pattern.endswith('$') else pattern
    while index < len(pattern):
        if pattern[index] == '*':
            index += 1
            continue
        count += 1
        index += 3 if pattern[index] == '%' and len(pattern) > index + 2 and all(c in '0123456789ABCDEF' for c in pattern[index + 1:index + 3]) else 1
    return count


class RobotsRules:
    def __init__(self, text):
        if len(text.encode('utf-8')) > 512_000:
            raise ValueError('robots.txtが解析上限（500KiB）を超えています。アクセス設定は不明です。')
        self.groups = []
        agents, rules, started = [], [], False
        for number, raw in enumerate(text.lstrip('\ufeff').splitlines(), 1):
            line = raw.split('#', 1)[0].strip()
            if ':' not in line: continue
            field, value = (part.strip() for part in line.split(':', 1))
            field = field.lower()
            if field == 'user-agent':
                if started:
                    self.groups.append((agents, rules))
                    agents, rules, started = [], [], False
                if value: agents.append(value.lower())
            elif field in ('allow', 'disallow') and agents:
                started = True
                if not value: continue
                # A non-empty rule path must start with a slash.
                if not value.startswith('/'): continue
                pattern = normalize_path(value)
                rules.append(dict(allowed=field == 'allow', pattern=pattern,
                                  rule=f'{field.title()}: {value}', line=number,
                                  length=specificity(pattern)))
        if agents: self.groups.append((agents, rules))

    def decision(self, bot, url):
        specific = [rules for agents, rules in self.groups if bot.lower() in agents]
        groups = specific if specific else [rules for agents, rules in self.groups if '*' in agents]
        group = bot if specific else ('*' if groups else 'なし')
        p = urlsplit(url)
        path = normalize_path((p.path or '/') + (('?' + p.query) if p.query else ''))
        candidates = [rule for rules in groups for rule in rules if matches(rule['pattern'], path)]
        if not candidates:
            return dict(allowed=True, matched_rule=None, matched_line=None, group=group,
                        reason='一致するAllow/Disallowルールがないため、ルール上は許可。')
        winner = max(candidates, key=lambda rule: (rule['length'], rule['allowed']))
        return dict(allowed=winner['allowed'], matched_rule=winner['rule'], matched_line=winner['line'], group=group,
                    reason='最長一致のルールを採用。同じ長さではAllowを優先。')
