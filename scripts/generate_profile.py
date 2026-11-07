"""Render repository-hosted profile cards using Python's standard library.

Run with GITHUB_TOKEN for live data, or --placeholder for an initial preview.
API failures exit before writing and preserve the last successful cards.
"""
import argparse
import collections
import datetime as dt
import html
import json
import os
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'generated'
GREEN = '#6ee7b7'
MUTED = '#8b9aab'


def text(x, y, value, size=14, color='#e6edf3', extra=''):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" {extra}>{html.escape(str(value))}</text>'


def card(width, height, title, subtitle, content):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img"><title>{html.escape(title)}</title>'
            f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="16" fill="#0d1117" stroke="#293440"/>'
            '<g font-family="Segoe UI,Arial,sans-serif">'
            + text(26, 35, title, 16, '#e6edf3', 'font-weight="600"')
            + text(26, 57, subtitle, 11, MUTED) + content + '</g></svg>')


def graphql(query, variables):
    request = urllib.request.Request('https://api.github.com/graphql',
        data=json.dumps({'query': query, 'variables': variables}).encode(),
        headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
                 'Content-Type': 'application/json', 'User-Agent': 'Sar-Chanrithy-profile'})
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.load(response)
    if result.get('errors'):
        raise RuntimeError('GitHub GraphQL: ' + '; '.join(e['message'] for e in result['errors']))
    return result['data']['user']


def fetch(username):
    user = graphql('''query($login:String!) { user(login:$login) {
      followers { totalCount }
      contributionsCollection { contributionCalendar {
        totalContributions weeks { contributionDays { date contributionCount contributionLevel } }
      } }
    } }''', {'login': username})
    if not user:
        raise RuntimeError('GitHub user not found')
    repos, cursor = [], None
    while True:
        page = graphql('''query($login:String!, $cursor:String) { user(login:$login) {
          repositories(first:100, after:$cursor, ownerAffiliations:OWNER,
            privacy:PUBLIC, isFork:false) {
            nodes { stargazerCount languages(first:100) { edges { size node { name color } } } }
            pageInfo { hasNextPage endCursor }
          }
        } }''', {'login': username, 'cursor': cursor})['repositories']
        repos.extend(page['nodes'])
        if not page['pageInfo']['hasNextPage']:
            break
        cursor = page['pageInfo']['endCursor']
    languages = collections.Counter()
    colors = {}
    for repo in repos:
        for edge in repo['languages']['edges']:
            name = edge['node']['name']
            languages[name] += edge['size']
            colors[name] = edge['node']['color'] or GREEN
    return {'calendar': user['contributionsCollection']['contributionCalendar'],
            'repos': len(repos), 'stars': sum(r['stargazerCount'] for r in repos),
            'followers': user['followers']['totalCount'],
            'languages': languages, 'colors': colors}


def render(data):
    ready = data is not None
    subtitle = ('Updated ' + dt.datetime.now(dt.timezone.utc).strftime('%d %b %Y · %H:%M UTC')) if ready else 'Awaiting first GitHub Actions update'
    calendar = data['calendar'] if ready else {'totalContributions': '—', 'weeks': []}
    metrics = [('Contributions · last year', calendar['totalContributions']),
               ('Public repos · non-forks', data['repos'] if ready else '—'),
               ('Stars · owned non-forks', data['stars'] if ready else '—'),
               ('Followers', data['followers'] if ready else '—')]
    body = ''
    for i, (label, value) in enumerate(metrics):
        x, y = 27 + (i % 2) * 232, 114 + (i // 2) * 88
        body += text(x, y, f'{value:,}' if isinstance(value, int) else value, 33, GREEN, 'font-weight="600"')
        body += text(x, y + 24, label, 12, MUTED)
    stats = card(490, 280, 'GitHub overview', subtitle, body)

    languages = data['languages'] if ready else {}
    total = sum(languages.values())
    top = sorted(languages.items(), key=lambda item: (-item[1], item[0]))[:6]
    body, offset = '', 27
    for name, size in sorted(languages.items(), key=lambda item: (-item[1], item[0])):
        width = 434 * size / total
        body += f'<rect x="{offset:.2f}" y="83" width="{width:.2f}" height="11" fill="{data["colors"][name]}"/>'
        offset += width
    for i, (name, size) in enumerate(top):
        x, y = 27 + (i % 2) * 232, 128 + (i // 2) * 43
        body += f'<circle cx="{x+4}" cy="{y-4}" r="4" fill="{data["colors"][name]}"/>'
        body += text(x + 16, y, name, 12) + text(x + 16, y + 16, f'{size / total:.1%}', 10, MUTED)
    if not top:
        body += text(27, 136, 'No language data yet' if ready else 'Your language mix will appear here.', 15, GREEN)
        body += text(27, 162, 'Measured from owned public repositories.', 12, MUTED)
    body += text(27, 258, 'BY CODE SIZE / PUBLIC REPOSITORIES / NO FORKS', 9, MUTED)
    langs = card(490, 280, 'Language mix', subtitle, body)

    weeks = calendar['weeks']
    values = [sum(day['contributionCount'] for day in w['contributionDays']) for w in weeks]
    peak = max(values, default=0) or 1
    body = ''
    for i in range(4):
        y = 90 + i * 44
        body += f'<path d="M48 {y}H964" stroke="#23303c" stroke-dasharray="3 6"/>'
        body += text(24, y + 4, round(peak * (3-i) / 3), 10, MUTED) if ready else ''
    if values:
        coords = [(48 + i * 916 / max(1, len(values)-1), 222 - v / peak * 132) for i, v in enumerate(values)]
        points = ' '.join(f'{x:.1f},{y:.1f}' for x, y in coords)
        body += f'<polygon points="48,222 {points} {coords[-1][0]:.1f},222" fill="#6ee7b7" fill-opacity=".08"/>'
        body += f'<polyline points="{points}" fill="none" stroke="{GREEN}" stroke-width="2.5" stroke-linejoin="round"/>'
        for index in range(0, len(weeks), 8):
            label = dt.date.fromisoformat(weeks[index]['contributionDays'][0]['date']).strftime('%b %Y')
            body += text(48 + index * 916 / max(1, len(values)-1), 250, label, 10, MUTED)
    else:
        body += text(500, 155, 'Your weekly activity will appear after the first sync.', 16, GREEN, 'text-anchor="middle"')
    activity = card(1000, 280, 'The contribution timeline', 'Weekly contributions · last year', body)

    body = ''
    levels = {'NONE': 0, 'FIRST_QUARTILE': 1, 'SECOND_QUARTILE': 2, 'THIRD_QUARTILE': 3, 'FOURTH_QUARTILE': 4}
    palette = ['#172a28', '#205640', '#27875a', '#3dc981', '#8cf0bb']
    for wi, week in enumerate(weeks):
        for day in week['contributionDays']:
            weekday = (dt.date.fromisoformat(day['date']).weekday() + 1) % 7
            x, y = 90 + wi * 14 + weekday * 18, 190 + weekday * 9 - wi * 1.7
            level = levels[day['contributionLevel']]
            height = 2 + level * 7
            body += f'<g><title>{day["date"]}: {day["contributionCount"]} contributions</title>'
            body += f'<path d="M{x} {y-height}l12 -6 14 8 -12 6Z" fill="{palette[level]}" stroke="#0d1117" stroke-width=".7"/>'
            body += f'<path d="M{x} {y-height}l14 8v{height}l-14 -8Z" fill="{palette[level]}" opacity=".48"/>'
            body += f'<path d="M{x+14} {y-height+8}l12 -6v{height}l-12 6Z" fill="{palette[level]}" opacity=".72"/></g>'
    if not weeks:
        body += text(500, 145, 'A year of small steps, rendered in 3D.', 18, GREEN, 'text-anchor="middle"')
        body += text(500, 174, 'Contribution columns appear after the first sync.', 13, MUTED, 'text-anchor="middle"')
    body += text(26, 290, 'LESS', 9, MUTED)
    for i, color in enumerate(palette):
        body += f'<rect x="{61+i*16}" y="280" width="11" height="11" rx="2" fill="{color}"/>'
    body += text(148, 290, 'MORE', 9, MUTED)
    body += text(974, 290, 'Each column is one day', 10, MUTED, 'text-anchor="end"')
    contributions = card(1000, 320, 'The contribution landscape', 'An isometric view · height follows GitHub contribution intensity', body)
    return {'stats.svg': stats, 'languages.svg': langs, 'activity.svg': activity, 'contributions.svg': contributions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--placeholder', action='store_true', help='Render honest empty states without network access')
    args = parser.parse_args()
    if not args.placeholder and not os.environ.get('GITHUB_TOKEN'):
        parser.error('GITHUB_TOKEN is required for live data; use --placeholder for a local preview')
    cards = render(None if args.placeholder else fetch(os.environ.get('PROFILE_USERNAME', 'Sar-Chanrithy')))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, svg in cards.items():
        (OUT / name).write_text(svg + '\n', encoding='utf-8')
    print(f'Rendered {len(cards)} profile cards.')


if __name__ == '__main__':
    main()
