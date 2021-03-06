# This file is part of Adblock Plus <https://adblockplus.org/>,
# Copyright (C) 2006-present eyeo GmbH
#
# Adblock Plus is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# Adblock Plus is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Adblock Plus.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import pytest

from abp.filters import (
    parse_line, parse_filterlist, ParseError,
    SELECTOR_TYPE as ST, FILTER_ACTION as FA, FILTER_OPTION as OPT,
)
from abp.filters.parser import Comment, Metadata


def test_parse_empty():
    line = parse_line('    ')
    assert line.type == 'emptyline'


@pytest.mark.parametrize('filter_text, expected', {
    # Blocking filters with patterns and regexps and blocking exceptions.
    '*asdf*d**dd*': {
        'selector': {'type': ST.URL_PATTERN, 'value': '*asdf*d**dd*'},
        'action': FA.BLOCK,
    },
    '@@|*asd|f*d**dd*|': {
        'selector': {'type': ST.URL_PATTERN, 'value': '|*asd|f*d**dd*|'},
        'action': FA.ALLOW,
    },
    '/ddd|f?a[s]d/': {
        'selector': {'type': ST.URL_REGEXP, 'value': 'ddd|f?a[s]d'},
        'action': FA.BLOCK,
    },
    '@@/ddd|f?a[s]d/': {
        'selector': {'type': ST.URL_REGEXP, 'value': 'ddd|f?a[s]d'},
        'action': FA.ALLOW,
    },
    # Blocking filters with some options.
    'bla$match-case,~script,domain=foo.com|~bar.com,sitekey=foo': {
        'selector': {'type': ST.URL_PATTERN, 'value': 'bla'},
        'action': FA.BLOCK,
        'options': [
            (OPT.MATCH_CASE, True),
            (OPT.SCRIPT, False),
            (OPT.DOMAIN, [('foo.com', True), ('bar.com', False)]),
            (OPT.SITEKEY, ['foo']),
        ],
    },
    '@@http://bla$~script,~other,sitekey=foo|bar': {
        'selector': {'type': ST.URL_PATTERN, 'value': 'http://bla'},
        'action': FA.ALLOW,
        'options': [
            (OPT.SCRIPT, False),
            (OPT.OTHER, False),
            (OPT.SITEKEY, ['foo', 'bar']),
        ],
    },
    # Element hiding filters and exceptions.
    '##ddd': {
        'selector': {'type': ST.CSS, 'value': 'ddd'},
        'action': FA.HIDE,
        'options': [],
    },
    '#@#body > div:first-child': {
        'selector': {'type': ST.CSS, 'value': 'body > div:first-child'},
        'action': FA.SHOW,
        'options': [],
    },
    'foo,~bar##ddd': {
        'options': [(OPT.DOMAIN, [('foo', True), ('bar', False)])],
    },
    # Element hiding emulation filters (extended CSS).
    'foo,~bar#?#:-abp-properties(abc)': {
        'selector': {'type': ST.XCSS, 'value': ':-abp-properties(abc)'},
        'action': FA.HIDE,
        'options': [(OPT.DOMAIN, [('foo', True), ('bar', False)])],
    },
    'foo.com#?#aaa :-abp-properties(abc) bbb': {
        'selector': {
            'type': ST.XCSS,
            'value': 'aaa :-abp-properties(abc) bbb',
        },
    },
    '#?#:-abp-properties(|background-image: url(data:*))': {
        'selector': {
            'type': ST.XCSS,
            'value': ':-abp-properties(|background-image: url(data:*))',
        },
        'options': [],
    },
}.items())
def test_parse_filters(filter_text, expected):
    """Parametric test for filter parsing."""
    parsed = parse_line(filter_text)
    assert parsed.type == 'filter'
    assert parsed.text == filter_text
    for attribute, expected_value in expected.items():
        assert getattr(parsed, attribute) == expected_value


def test_parse_comment():
    line = parse_line('! Block foo')
    assert line.type == 'comment'
    assert line.text == 'Block foo'


def test_parse_meta():
    line = parse_line('! Homepage  :  http://aaa.com/b')
    assert line.type == 'metadata'
    assert line.key == 'Homepage'
    assert line.value == 'http://aaa.com/b'


def test_parse_nonmeta():
    line = parse_line('! WrongHeader: something')
    assert line.type == 'comment'


def test_parse_instruction():
    line = parse_line('%include foo:bar/baz.txt%')
    assert line.type == 'include'
    assert line.target == 'foo:bar/baz.txt'


def test_parse_bad_instruction():
    with pytest.raises(ParseError):
        parse_line('%foo bar%')


def test_parse_header():
    line = parse_line('[Adblock Plus 1.1]')
    assert line.type == 'header'
    assert line.version == 'Adblock Plus 1.1'


def test_parse_bad_header():
    with pytest.raises(ParseError):
        parse_line('[Adblock 1.1]')


def test_parse_filterlist():
    result = parse_filterlist(['! foo', '! Title: bar'])
    assert list(result) == [Comment('foo'), Metadata('Title', 'bar')]


def test_exception_timing():
    result = parse_filterlist(['! good line', '%bad line%'])
    assert next(result) == Comment('good line')
    with pytest.raises(ParseError):
        next(result)


def test_parse_line_bytes():
    line = parse_line(b'! \xc3\xbc')
    assert line.text == '\xfc'
