#!/usr/bin/env python3
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

import os
import sys
import importlib
import inspect
import pkgutil
import itertools
import logging
import json
import time
import traceback

import praw

__author__ = 'kupiakos'
__version__ = '0.1'


class LapisLazuli:
    """Lapis Lazuli's Mirror didn't disappear; it just ascended into cyberspace."""

    sr = None
    reddit = None
    options = None
    plugins = None
    log = None
    ch = None

    def __init__(self, **kwargs):
        assert isinstance(kwargs, dict)
        self.options = kwargs
        self.log = logging.getLogger('lapis')
        self.log.setLevel(logging.DEBUG)
        if self.log.hasHandlers():
            for handler in self.log.handlers:
                self.log.removeHandler(handler)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter('%(levelname)-5s - %(message)s'))
        self.log.addHandler(ch)
        if kwargs.get('logfile'):
            logfile = logging.FileHandler(
                os.path.join(get_script_dir(), kwargs['logfile']))
            logfile.setLevel(logging.DEBUG)
            logfile.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)-12s - %(levelname)-5s - %(message)s'))
            self.log.addHandler(logfile)
        self.log.info(' --- STARTING LAPIS MIRROR --- ')
        self.load_plugins()
        self.verify_options()
        self.login()

    def call_plugin_function(self, func_name, *args, **kwargs):
        self.log.debug('Calling %s() on plugins', func_name)
        returns = []
        for plugin in itertools.chain(self.plugins):
            if hasattr(plugin, func_name):
                self.log.debug('Calling %s.%s()', plugin.__class__.__name__, func_name)
                returns.append(getattr(plugin, func_name)(*args, **kwargs))
            else:
                self.log.debug('%s does not have a %s() function', plugin.__class__.__name__, func_name)
        return returns

    def get_submission_by_id(self, sub_id):
        url = 'https://www.reddit.com/r/{0}/comments/{1}/_/'.format(self.options['subreddit'], sub_id)
        return self.reddit.get_submission(url=url)

    def load_plugins(self):
        self.plugins = []
        if 'plugins_dir' not in self.options:
            self.options['plugins_dir'] = 'plugins'
            self.log.warning('plugins_dir not defined, using ' + self.options['plugins_dir'])

        self.options['plugins_package'] = self.options.get(
            'plugins_package',
            self.options['plugins_dir']).replace('.', os.path.sep)
        self.options['plugins_dir'] = os.path.join(get_script_dir(), self.options['plugins_dir'])

        self.log.debug('plugins_dir: ' + self.options['plugins_dir'])
        self.log.debug('plugins_package: ' + self.options['plugins_package'])

        for module in (importlib.import_module(name)
                       for ff, name, ispkg in
                       pkgutil.iter_modules([self.options['plugins_dir']],
                                            self.options['plugins_package'] + '.')
                       if not ispkg):
            self.log.debug('Parsing module ' + repr(module))
            plugin = getattr(module, '__plugin__', None)
            if inspect.isclass(plugin):
                self.log.info('Initializing plugin ' + plugin.__name__)
                self.plugins.append(plugin(**self.options))

    def login(self):
        self.log.info('Logging into Reddit...')
        self.reddit = praw.Reddit(user_agent=self.options['user_agent'])
        self.reddit.login(username=self.options['reddit_user'],
                          password=self.options['reddit_password'])
        self.sr = self.reddit.get_subreddit(self.options['subreddit'])
        self.call_plugin_function('login')

    def process_submission(self, submission):
        self.log.debug('Processing submission\n'
                       '        permalink:%s\n'
                       '        url:      %s',
                       submission.permalink, submission.url)
        if any(comment.author.name == self.options['reddit_user']
               for comment in submission.comments if comment.author):
            self.log.debug('Have already commented here--moving on.')
            return

        import_results = self.call_plugin_function('import_submission', submission=submission)
        if not any(import_results):
            self.log.debug('No processing done on "%s"', submission.url)
            return
        self.log.info('\n\nImported data from submission "%s"', submission.url)
        export_table = []
        for import_info in filter(None, import_results):
            self.log.debug('Import info: %s', str(import_results))
            # export_results.append((import_info.get('importer_display', ''),
            export_results = self.call_plugin_function('export_submission', **import_info)
            if not any(export_results):
                continue
            importer_display = import_info.get('importer_display', {})
            export_table.append((importer_display, export_results))

        if not any(export_table):
            self.log.warning('Imports done, but no exports.')
            return

        links_display_parts = []
        for importer_display, export_results in export_table:
            links_display_parts.append(importer_display.get('header', ''))
            for export_result in export_results:
                links_display_parts.append(export_result.get('link_display'))
            links_display_parts.append(importer_display.get('footer', ''))
        links_display = ''.join(links_display_parts)
        text = self.options.get('post_template',
                                '{links}\n\n---\n^(Lapis Mirror {version})').format(
            links=links_display, **self.options)
        try:
            submission.add_comment(text)
            self.log.info('Replied comment to %s', submission.url)
        except Exception:
            self.log.error('Had an error posting to Reddit! Attempting cleanup:\n%s', traceback.format_exc())
            try:
                for _, export_results in export_table:
                    for export_result in export_results:
                        if 'delete_info' in export_result and 'exporter' in export_result:
                            matched = [i for i in self.plugins
                                       if i.__class__.__name__ == export_result['exporter'] and
                                       hasattr(i, 'delete_export')]
                            for match in matched:
                                match.delete_export(**export_result)
            except Exception:
                self.log.error('Error while attempting to delete exports:\n%s', traceback.format_exc())
            return
            # TODO: Implement SQLite log
            # submission_id = submission.id
            # comment_id = comment.id

    def scan_submissions(self, delay=False):
        done = []
        while True:
            for submission in self.sr.get_new(limit=self.options.get('scan_limit', 50)):
                if submission.id not in done:
                    self.process_submission(submission)
                done.append(submission.id)
                if delay:
                    input()
            # self.log.debug('Waiting before next check')
            time.sleep(self.options.get('delay_interval', 30))

    def verify_options(self):
        if 'version' not in self.options:
            self.options['version'] = __version__
        if 'subreddit' not in self.options:
            raise LapisError('You must define a subreddit!')
        if 'reddit_user' not in self.options:
            raise LapisError('You must define a user!')
        if 'reddit_password' not in self.options:
            raise LapisError('You must define a password!')
        if 'maintainer' not in self.options:
            raise LapisError('You must define a maintainer!')
        if 'user_agent' not in self.options:
            self.options['user_agent'] = '{name}/{version} by {maintainer}'.format(
                name='LapisMirror', **self.options)
        self.call_plugin_function('verify_options', self.options)


def get_script_dir():
    try:
        return os.path.dirname(__file__)
    except NameError:
        return os.path.dirname(os.path.realpath(sys.argv[0]))


class LapisError(Exception):
    """Good job, you made Lapis cry."""


def main():
    config_path = os.path.join(get_script_dir(), 'lapis.conf')
    if not os.path.isfile(config_path):
        raise LapisError('No configuration file found at {}'.format(config_path))
    with open(config_path) as config_file:
        config = json.load(config_file)
    lapis = LapisLazuli(**config)
    while True:
        try:
            lapis.scan_submissions()
        except Exception:
            lapis.log.error('Error while scanning submission! %s', traceback.format_exc())
            lapis = LapisLazuli(**config)


if __name__ == '__main__':
    main()

# END OF LINE.
