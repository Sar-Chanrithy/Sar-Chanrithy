"""Offline checks for data aggregation and SVG output; fixtures are not profile data."""
import collections
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import generate_profile as profile


class ProfileTests(unittest.TestCase):
    def test_empty_cards_are_honest_valid_svg(self):
        cards = profile.render(None)
        self.assertEqual(len(cards), 4)
        for svg in cards.values():
            ET.fromstring(svg)
        self.assertIn('Awaiting first GitHub Actions update', cards['stats.svg'])
        self.assertNotIn('nan', ''.join(cards.values()).lower())

    def test_zero_activity_and_no_languages(self):
        data = self.fixture()
        for svg in profile.render(data).values():
            ET.fromstring(svg)
        self.assertIn('No language data yet', profile.render(data)['languages.svg'])

    def test_language_percentages_and_escape(self):
        data = self.fixture()
        data['languages'] = collections.Counter({'A&B': 75, 'Python': 25})
        data['colors'] = {'A&B': '#abcdef', 'Python': '#123456'}
        svg = profile.render(data)['languages.svg']
        ET.fromstring(svg)
        self.assertIn('75.0%', svg)
        self.assertIn('25.0%', svg)
        self.assertIn('A&amp;B', svg)

    def test_calendar_uses_real_weekdays_in_partial_week(self):
        data = self.fixture()
        data['calendar']['weeks'] = [{'contributionDays': [
            {'date': '2026-11-07', 'contributionCount': 4, 'contributionLevel': 'FOURTH_QUARTILE'}]}]
        data['calendar']['totalContributions'] = 4
        result = profile.render(data)
        for svg in result.values():
            ET.fromstring(svg)
        self.assertIn('2026-11-07: 4 contributions', result['contributions.svg'])
        self.assertIn('M198 214.0', result['contributions.svg'])

    def test_repository_pagination_and_language_aggregation(self):
        def repository(stars, size):
            return {'stargazerCount': stars, 'languages': {'edges': [
                {'size': size, 'node': {'name': 'Python', 'color': '#3572a5'}}]}}
        responses = [
            {'followers': {'totalCount': 7}, 'contributionsCollection': {'contributionCalendar': {'totalContributions': 8, 'weeks': []}}},
            {'repositories': {'nodes': [repository(2, 30)], 'pageInfo': {'hasNextPage': True, 'endCursor': 'next-page'}}},
            {'repositories': {'nodes': [repository(3, 70)], 'pageInfo': {'hasNextPage': False, 'endCursor': None}}},
        ]
        with patch.object(profile, 'graphql', side_effect=responses) as request:
            result = profile.fetch('example')
        self.assertEqual(result['repos'], 2)
        self.assertEqual(result['stars'], 5)
        self.assertEqual(result['languages']['Python'], 100)
        self.assertEqual(request.call_args_list[2].args[1]['cursor'], 'next-page')

    @staticmethod
    def fixture():
        return {'calendar': {'totalContributions': 0, 'weeks': []},
                'repos': 0, 'stars': 0, 'followers': 0,
                'languages': collections.Counter(), 'colors': {}}


if __name__ == '__main__':
    unittest.main()
