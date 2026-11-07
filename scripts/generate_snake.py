"""Build an animated snake from the publicly visible GitHub contribution calendar."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
import os
import re


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag != 'td' or 'data-date' not in attrs or 'data-level' not in attrs:
            return
        match = re.fullmatch(r'contribution-day-component-([0-6])-(\d+)', attrs.get('id', ''))
        if not match:
            return
        row, week = map(int, match.groups())
        level = int(attrs['data-level'])
        if not 0 <= level <= 4:
            raise ValueError('Invalid contribution level')
        self.days[(week, row)] = (attrs['data-date'], level)


def read_calendar(username):
    if not re.fullmatch(r'[A-Za-z0-9-]+', username):
        raise ValueError('Invalid GitHub username')
    request = Request(f'https://github.com/users/{username}/contributions',
                      headers={'User-Agent': 'github-profile-snake'})
    with urlopen(request, timeout=60) as response:
        parser = Calendar()
        parser.feed(response.read().decode('utf-8'))
    weeks = max((week for week, _ in parser.days), default=-1) + 1
    if not 52 <= weeks <= 54 or not 350 <= len(parser.days) <= 378:
        raise ValueError(f'Unexpected GitHub calendar: {weeks} weeks, {len(parser.days)} days')
    return parser.days, weeks


def render(days, weeks, dark):
    colors = (['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353'] if dark
              else ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'])
    duration = 48
    positions = [(week, row) for week in range(weeks)
                 for row in (range(7) if week % 2 == 0 else range(6, -1, -1))]
    total = len(positions)
    coords = lambda week, row: (week * 16 + 8, row * 16 + 8)
    path = ' '.join(('M' if i == 0 else 'L') + ' '.join(map(str, coords(*pos)))
                    for i, pos in enumerate(positions))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-4 -4 {weeks*16+8} 120" '
             f'width="{weeks*16+8}" height="120" role="img">',
             '<title>GitHub contributions with animated snake</title>', '<style>']
    for i, pos in enumerate(positions):
        if pos not in days or not days[pos][1]:
            continue
        level = days[pos][1]
        cutoff = min(99.9, i * 100 / (total - 1))
        before = max(0, cutoff - 0.02)
        parts.append(f'@keyframes eat{i}{{0%,{before:.3f}%{{fill:{colors[level]}}}'
                     f'{cutoff:.3f}%,100%{{fill:{colors[0]}}}}}')
        parts.append(f'.day{i}{{fill:{colors[level]};animation:eat{i} {duration}s linear infinite}}')
    parts.append('</style>')
    for i, (week, row) in enumerate(positions):
        if (week, row) not in days:
            continue
        date, level = days[(week, row)]
        css = f' class="day{i}"' if level else f' fill="{colors[0]}"'
        parts.append(f'<rect x="{week*16+2}" y="{row*16+2}" width="12" height="12" rx="2"{css}>'
                     f'<title>{date}: contribution level {level}</title></rect>')
    for segment in range(4, -1, -1):
        radius = 6 if segment == 0 else 5
        opacity = 1 - segment * .1
        parts.append(f'<circle r="{radius}" fill="#a020b0" opacity="{opacity}">'
                     f'<animateMotion dur="{duration}s" begin="-{segment*.14}s" repeatCount="indefinite" '
                     f'calcMode="linear" path="{path}"/></circle>')
    parts.append('</svg>')
    return ''.join(parts)


def main():
    username = os.environ.get('GITHUB_REPOSITORY_OWNER', 'Sar-Chanrithy')
    days, weeks = read_calendar(username)
    output = Path('dist')
    output.mkdir(exist_ok=True)
    for filename, dark in [('github-snake.svg', False), ('github-snake-dark.svg', True)]:
        (output / filename).write_text(render(days, weeks, dark), encoding='utf-8')
    active = sum(level > 0 for _, level in days.values())
    print(f'Generated snake from {len(days)} calendar days ({active} active days).')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'::error::Snake generation failed: {type(exc).__name__}: {exc}')
        raise
