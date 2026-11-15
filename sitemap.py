"""Bounded sitemap candidate extraction. No recursive fetches or XML entities."""
import re
from urllib.parse import urlsplit, urlunsplit
from xml.etree import ElementTree as ET


def parse_sitemap(body, source, validate):
    if len(body.encode('utf-8')) > 2_000_000:
        raise ValueError('サイトマップの上限（2MB）を超えています。')
    if re.search(r'<!\s*(DOCTYPE|ENTITY)', body, re.I):
        raise ValueError('DTD・外部実体を含むXMLには対応していません。')
    try: root = ET.fromstring(body)
    except (ET.ParseError, RecursionError): raise ValueError('サイトマップXMLを解析できませんでした。') from None
    namespace = '{http://www.sitemaps.org/schemas/sitemap/0.9}' if root.tag.startswith('{http://www.sitemaps.org/schemas/sitemap/0.9}') else ''
    if root.tag not in (namespace+'urlset', namespace+'sitemapindex'):
        raise ValueError('urlset または sitemapindex 形式のXMLを指定してください。')
    kind = 'pages' if root.tag == namespace+'urlset' else 'index'
    item_tag = namespace + ('url' if kind == 'pages' else 'sitemap')
    host = urlsplit(source).hostname
    urls, seen, skipped = [], set(), 0
    truncated = False
    for item in root.findall(item_tag):
        loc = item.find(namespace+'loc')
        value = (loc.text or '').strip() if loc is not None else ''
        try:
            p = validate(value)
            if p.hostname != host: raise ValueError('different host')
        except ValueError:
            skipped += 1
            continue
        value = urlunsplit(p._replace(fragment=''))
        if value in seen: continue
        seen.add(value)
        if len(urls) == 100:
            truncated = True
            continue
        urls.append(value)
    return dict(source=source, kind=kind, urls=urls, skipped=skipped, truncated=truncated)
