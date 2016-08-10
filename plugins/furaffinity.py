# The MIT License (MIT)

# Copyright (c) 2015 kupiakos

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import logging
import re
from typing import Iterable, Optional
from urllib.parse import urljoin
import traceback

import requests
import bs4
import praw

# The maximum number of pages to search in a gallery
MAX_PAGES = 20


class FurAffinityPlugin:
    """A plugin for FurAffinity, requested by /r/zootopia.

    FurAffinity has no API, so HTML hacks had to be used.
    """

    def __init__(self, useragent: str, **_):
        """Initialize the FA import API.

        :param useragent: The useragent to use for querying FA.
        :param options: Other options in the configuration. Ignored.
        """
        self.log = logging.getLogger('lapis.furaffinity')
        self.headers = {'User-Agent': useragent}
        self.regex = re.compile(
            r'^https?://('
            r'((?:www\.)?(?:sfw\.)?furaffinity\.net/view/(?P<id>\d+).*)|'
            r'(d\.facdn\.net/art/(?P<artist>[^/]+)/(?P<cdn_id>\d+)/.*)'
            r')$')

    def get(self, url: str) -> Optional[str]:
        r = requests.get(url, headers=self.headers)
        return r.text if r.ok else None

    def import_submission(self, submission: praw.objects.Submission) -> dict:
        """Import a submission from FA. Uses raw HTML scraping.

        Because this downloads the page and tries to scrape the HTML,
        we are at significant risk of the image ID on the DOM changing.
        Therefore, this plugin is liable to break.

        This function will define the following values in its return data:
        - author: the artist defined by FA for the submission
        - source: The url of the submission, or locating the FA submission if possible
        - importer_display/header
        - import_urls

        :param submission: A reddit submission to parse.
        """
        try:
            match = self.regex.match(submission.url)
            if not match:
                return None
            match_data = match.groupdict()

            submission_id = match_data.get('id')
            artist = match_data.get('artist')

            data = {'source': submission.url,
                    'importer_display': {}
                    }

            if match_data['cdn_id'] is not None:
                data['import_urls'] = [submission.url]
                submission_id = self.find_submission_from_cdn(
                    match_data['artist'], match_data['cdn_id'])

            if submission_id is None:
                # A submission could not be found from the CDN URL
                if artist:
                    artist_display = 'the artist "{}"'.format(self.user_page(artist))
                else:
                    artist_display = 'an Unknown artist'
                data['author'] = artist or 'an Unknown FA artist'
                data['importer_display']['header'] = (
                    'Mirrored FA image from {}:\n\n'.format(artist_display)
                )
                if not data.get('import_urls'):
                    return None
                return data

            submission_url = 'https://www.furaffinity.net/view/{}/'.format(submission_id)
            markup = self.get(submission_url)
            if not markup:
                raise IOError('Page could not be loaded')
            data['source'] = submission_url
            submission_page = bs4.BeautifulSoup(markup, 'lxml')
            artist = submission_page.select_one('td.cat a')
            artist = artist and artist.text.strip()
            data['author'] = artist or 'an Unknown FA artist'
            title = submission_page.select_one('td.cat b')
            title = title.text.strip() if title else 'an Unknown title'

            # One may be convinced to always use #submissionImg,
            # but it's possible for it to contain a small thumbnail URL.
            image_url = None
            url_script = submission_page.select_one('#page-submission .alt1 script')
            if url_script:
                m = re.search(r'var\s+full_url\s*=\s*"(?P<url>[^"]+)"\s*;', url_script.text)
                if m:
                    image_url = m.group('url')
            # If we couldn't find the image url through the script, go with the more rigorous way.
            if image_url is None:
                image_element = submission_page.find(id='submissionImg')
                if image_element is None or 'src' not in image_element:
                    raise ValueError('Image URL could not be found')
                image_url = image_element['src']
            # Make sure the image URL is absolute.
            image_url = urljoin(submission_url, image_url)
            assert image_url
            data['import_urls'] = [image_url]
            data['importer_display']['header'] = (
                'Mirrored "[{}]({})" by FA artist "{}":\n\n'.format(
                    title,
                    submission_url,
                    self.user_page(artist) if artist else data['author']
                )
            )
            return data
        except Exception:
            self.log.error('Could not import submission page %s: %s',
                           submission.url, traceback.format_exc())
            return None

    def find_submission_from_cdn(self, artist: str, cdn_id: str) -> Optional[str]:
        """Find the original submission of a posted FA CDN image.

        While there's no simple reverse-lookup that can be done a la DeviantArt,
        the thumbnail on a user's gallery page does contain the CDN ID.
        This will search through the user's gallery page looking for a matching thumbnail.

        :param artist: The artist name, extracted from the image URL.
        :param cdn_id: The CDN ID, extracted from the image URL.
        :return: A submission ID if found, None if not.
        """
        self.log.debug('Finding submission from CDN with artist %s, cdn_id, %s', artist, cdn_id)
        try:
            for gallery_page in self.enum_user_gallery(artist):
                thumbnail = gallery_page.select_one('.t-image img[src*="{}"]'.format(cdn_id))
                if thumbnail is not None:
                    break
            else:
                # No matching thumbnail was found
                return None
            m = re.match(r'.*/(?P<id>\d+)@\d+-\d+\.\w+$', thumbnail['src'])
            submission_id = m and m.group('id')
            self.log.debug('Found submission ID: %s', submission_id)
            return submission_id
        except Exception as e:
            self.log.warning('Could not import direct URL, artist: %s, cdn_id: %s',
                             artist, cdn_id)
            self.log.warning('Reason: %s', traceback.format_exc())
            return None

    def enum_user_gallery(self, artist: str) -> Iterable[bs4.BeautifulSoup]:
        """Enumerate through `MAX_PAGES` pages of a user's FA profile.

        :param artist: The name of the FA user.
        :return: A generator that returns BeautifulSoup pages for each gallery page.
        """
        page = 1
        more_pages = True
        while more_pages:
            gallery_url = (
                'https://www.furaffinity.net/gallery/'
                '{artist}/{page}?perpage=72'.format(artist=artist, page=page))
            self.log.debug('Loading gallery page %s', gallery_url)
            page = self.get(gallery_url)
            if not page:
                break
            bs = bs4.BeautifulSoup(page, 'lxml')
            yield bs
            next_page_link = bs.select_one('.pagination .button-link.right')
            more_pages = next_page_link is not None and 'href' in next_page_link
            page += 1
            if page > MAX_PAGES:
                break

    @staticmethod
    def user_page(artist: str) -> str:
        return '[{0}](https://www.furaffinity.net/user/{0}/)'.format(artist)


__plugin__ = FurAffinityPlugin

# END OF LINE.
