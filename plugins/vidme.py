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
import requests


class VidmePlugin:
    """A vid.me export plugin. Here's where magic turns to sorcery.

    Will upload a single video (currently supported via tumblr).
    You must have a vid.me account for this to be used.
    """

    auth_token = None
    username = None
    password = None

    def __init__(self, useragent: str, vidme_user: str='',
                 vidme_password: str='', **options):
        """Initialize the vid.me export API.

        :param useragent: The useragent to use for the vid.me API.
        :param vidme_user: The username with which to login to vid.me
        :param vidme_password: The password with which to login to vid.me
        :param options: Other passed options. Unused.
        """
        self.log = logging.getLogger("lapis.vidme")
        self.useragent = useragent
        self.username = vidme_user
        self.password = vidme_password
        self.headers = {'User-Agent': self.useragent}

    def login(self):
        """Attempt to log into the vid.me API, getting an auth token."""
        self.log.info('Logging into vid.me with username %s...', self.username)
        response = requests.post('https://api.vid.me/auth/create',
                                 params={'username': self.username,
                                         'password': self.password},
                                 headers=self.headers)
        if not response.ok:
            self.log.error('There was an error logging in!')
            self.log.error(response.json().get('error'))
        token = response.json()['auth']['token']
        self.headers['AccessToken'] = token

    def _check_login(self) -> bool:
        """Check if we are logged into vid.me with a proper access token.

        :return: A boolean designating whether we are successfully logged in.
        """
        try:
            response = requests.post('https://api.vid.me/auth/check',
                                     headers=self.headers)
            if not response.ok:
                self.log.error('Could not check for log-in status.')
                self.log.error(response.json().get('error'))
                return False
            return response.json()['status']
        except Exception:
            return False

    def export_submission(self,
                          import_urls: list,
                          author: str='an Unknown Author',
                          source: str='an Unknown Source',
                          video: bool=False,
                          **import_info) -> dict:
        """Upload a single (first if multiple are posted) video.

        Doesn't support images. Requires direct link or YouTube.

        This function will define the following values in the export data:
        - exporter
        - link_display

        :param import_urls: A list, len 1, of direct video links.
        :param author: The author to note in the description.
        :param source: The source to note in the description.
        :param video: Whether this is a video or not. Only works if it is.
        :param import_info: Other importing information passed. Ignored.
        :return: None if no export, an export info dictionary otherwise.
        """
        # vid.me is for videos, and videos only.
        if not (video and import_urls):
            return None
        try:
            if not self._check_login():
                self.login()
        except Exception:
            self.log.error('Could not log in to vid.me.')
            return None

        results = {'exporter': self.__class__.__name__}
        url = import_urls[0]
        description = ('This is a mirror uploaded by /u/LapisMirror, '
                       'originally made by %s, located at %s' %
                       (author, source))
        title = ('Lapis Mirror - video from %s' % author)

        self.log.debug('Will upload a single video to vid.me: %s', url)
        request = requests.post('https://api.vid.me/grab',
                                params={'url': url,
                                        'title': title,
                                        'description': description},
                                headers=self.headers)

        if not request.ok or not request.json()['status']:
            self.log.error('Could not upload video to vid.me:')
            self.log.error(request.json().get('error'))
            return None
        video_info = request.json()

        results['link_display'] = '[vid.me mirror]({}) ([embedded]({}))  \n'.format(
            video_info['url'], video_info['video']['embed_url'])

        return results


__plugin__ = VidmePlugin

# END OF LINE.
