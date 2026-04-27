###
# Copyright (c) 2016, Znuff
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import urllib.parse
import re
import requests
from bs4 import BeautifulSoup

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Bluray')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x

def get(url, post=False, data=None):
    headers = {
            'Pragma': 'no-cache',
            'Accept-Language': 'en-US,en;q=0.8,ro;q=0.6',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': url,
            'Cache-Control': 'no-cache',
            'X-Requested-With': 'XMLHttpRequest',
            }

    try:
        if post:
            resp = requests.post(url, headers=headers, data=data, timeout=10)
        else:
            resp = requests.get(url, headers=headers, timeout=10)
    except requests.exceptions.RequestException:
        resp = None

    return resp

def parse(resp):
    return BeautifulSoup(resp.content, 'html5lib')

def _err(movie, msg):
    return format('%s: %s', ircutils.bold(movie), msg)

def _check_response(resp):
    if resp is None:
        return 'network error'
    if not resp.ok:
        return 'HTTP %s' % resp.status_code
    return None

class Bluray(callbacks.Plugin):
    """Blu-Ray release dates"""
    threaded = True

    def bd(self, irc, msg, args, movie):
        """-- usage: bd <movie>

        """
        url = 'https://www.blu-ray.com/search/quicksearch.php'
        data = {'section': 'bluraymovies',
                'userid': '-1',
                'country': 'US',
                'keyword': movie}
        resp = get(url, post=True, data=data)

        err = _check_response(resp)
        if err:
            irc.reply(_err(movie, "can't find the coconut (%s)" % err))
            return

        soup = parse(resp)
        li = soup.find('li')
        if not li:
            irc.reply(_err(movie, "can't find the coconut"))
            return

        moviename = li.contents[2].replace('\xa0', '').strip()
        date = li.find('span').text
        if date == '-':
            date = 'not announced'

        movie_url = ''
        url_match = re.search(r"var urls = new Array\('([^']+)'", resp.text)
        if url_match:
            movie_url = ' \u2022 ' + url_match.group(1)

        irc.reply(format('%s: %s%s', ircutils.bold(moviename), date, movie_url))

    bd = wrap(bd, ['text'])

    def br(self, irc, msg, args, movie):
        """-- usage: br <movie>

        """
        base = 'https://www.dvdsreleasedates.com'
        # livesearch first
        url = base + '/livesearch.php?' + urllib.parse.urlencode({'q': movie})

        resp = get(url)

        err = _check_response(resp)
        if err:
            irc.reply(_err(movie, 'the coconut has resisted our attempts! (%s)' % err))
            return

        soup = parse(resp)
        link = soup.find('a')

        # follow the first link, if it exists
        if link:
            url = base + link['href']
            resp = get(url)

        # if not, let's try the non-live search form
        else:
            url = base + '/search.php'
            resp = get(url, post=True, data={'searchStr': movie})
            # results page
            if resp and resp.ok:
                soup = parse(resp)
                dvdcell = soup.find('td', {'class': 'dvdcell'})
                if not dvdcell:
                    irc.reply(_err(movie, "can't find the coconut"))
                    return
                url = base + dvdcell.find('a')['href']
                resp = get(url)

        err = _check_response(resp)
        if err:
            irc.reply(_err(movie, 'the coconut has resisted our attempts! (%s)' % err))
            return

        soup = parse(resp)
        h1 = soup.find('h1')
        moviename = h1.find('span', {'itemprop': 'name'}).text.strip()
        year = h1.find('a')
        if year:
            moviename = '%s (%s)' % (moviename, year.text)

        dates = soup.find('h2')
        if dates:
            # get all dates
            dates = dates.find_all('span')
            if len(dates) > 1:
                irc.reply(format('%s: %s (%s), %s (digital) \u2022 %s',
                        ircutils.bold(moviename),
                        ircutils.mircColor(dates[0].text, 'green'),
                        ircutils.mircColor('Blu-ray', 'blue'),
                        ircutils.mircColor(dates[1].text, 'red'),
                        url))
            else:
                irc.reply(format('%s: %s \u2022 %s',
                        ircutils.bold(moviename),
                        ircutils.mircColor(dates[0].text, 'green'),
                        url))

        # older movies don't have a release date in the database
        # maybe use the other source for this?
        else:
            irc.reply(_err(movie, "shit's too old \u2022 %s" % url))

    br = wrap(br, ['text'])

Class = Bluray

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
