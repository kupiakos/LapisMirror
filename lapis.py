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
from mako.template import Template

__author__ = 'kupiakos'
__version__ = '0.7'


class LapisLazuli:
    """_Lapis Lazuli's Mirror didn't disappear; it just ascended into cyberspace._

    Lapis Mirror imports modules from a plugin directory dynamically and loads them.
    So far, there are import and export modules.

    ### Importing and Exporting ###

    "Import" means to scrape an image from some site, such as deviantArt, and provide
    the raw URLs to the medium, as well as some other info as well.

    The data stored in an import info dictionary can be:
    - author: The name of the author or creator of the medium, if any.
    - source: Where the medium came from.
    - import_display: A dictionary with the possible values header and footer.
    It defines what to put above and below the export links.
    - import_urls: A list of URLs to be exported. The most important field.

    "Export" means to take an imported image, video, etc., and upload it to a specific
    site to host as a mirror. This includes sites such as imgur, vid.me, or gyfcat.

    The data stored in an export info dictionary can be:
    - exporter: The name of the class that exported this. Used for deletion.
    - link_display: The raw Markup text to represent the link.
    - delete_info: The information required to delete this image.

    ### The Lapis Process ###

    When `scan_submissions` is called, Lapis processes the last (default 50)
    Reddit posts and calls `import_submission` for each plugin on the submission.
    Then, each import_info dictionary is passed to each export. For each import
    processed on all exports, we bind the list of results with the import display.
    We are left with a list(dict, list(dict)).
    In retrospect, OOP may have been simpler.

    ### Creating Plugins ###

    To create a plugin, you must put a python module in the plugins directory.
    It must have a plugin class, named whatever you please.
    However, somewhere in the module, usually at the bottom, there must be a special
    variable `__plugin__` defined, set to the class you would like to be used.

    Plugins should define one or more of these functions to be of any use:
    - `__init__` - This will be called when Lapis is starting up.
    - `import_submission` - This is what defines an import module.
    - `export_submission` - This is what defines an export module.
    - `delete_export` - This is used to delete uploads already made.
    - `login` - In case our service needs to perform one login at start.
    - `verify_options` - Ensure that the configuration contains valid info.

    Generally, plugin functions should accept a kwargs argument to absorb any
    extraneous options that will inevitably be passed in.

    """

    sr = None
    reddit = None
    options = None
    plugins = None
    log = None
    ch = None
    use_oauth = False
    access_information = None
    username = None
    use_mako = False
    mako_template = None

    def __init__(self, **kwargs):
        """Initialize the Lapis Lazuli Mirroring System.
        Will start logging immediately.

        :param kwargs: All configuration options provided from lapis.conf.
        """
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
        self.verify_options()
        self.login()
        self.load_plugins()
        self.call_plugin_function('verify_options', self.options)
        self.call_plugin_function('login')

    def call_plugin_function(self, func_name: str, *args, **kwargs) -> list:
        """Call all registered plugins with function <func_name>.

        For example, if you have three proper import plugins, and
        two proper export plugins::
            len(call_plugin_function('import_submission', submission)) == 3
            len(call_plugin_function('export_submission', submission)) == 2

        It is standard for failed imports and exports to return None if they
        cannot process the given submission.

        :param func_name: The name of the function to call for each plugin.
        :param args: The positional arguments with which to call the function.
        :param kwargs: The named arguments with which to call the function.
        :return: A list of the values returned from the plugins with the function.
        """
        self.log.debug('Calling %s() on plugins', func_name)
        returns = []
        for plugin in itertools.chain(self.plugins):
            display_name = '%s.%s()' % (plugin.__class__.__name__, func_name)
            try:
                if hasattr(plugin, func_name):
                    # self.log.debug('Calling %s', display_name)
                    import_data = getattr(plugin, func_name)(*args, **kwargs)
                    if import_data:
                        self.log.info('Successfully imported data from %s.%s()',
                                      plugin.__class__.__name__, func_name)
                        returns.append(import_data)
                # else:
                #     self.log.debug('%s does not have a display_name() function',
                #                    plugin.__class__.__name__, func_name)
            except Exception:
                self.log.error('Error occurred while calling %s:\n%s',
                               display_name, traceback.format_exc())
        return returns

    def forward_reply(self, item):
        try:
            item.mark_as_read()
            response = '{}{}'.format(
                item.body,
                '  \n[Context]({})'.format(item.context)
                if hasattr(item, 'context') else '')
            self.log.info('Forwarding a reply from {}:  \n{}'.format(
                item.author.name, item.body))
            self.reddit.send_message(self.options['maintainer'],
                                     '{} forward from {}'.format(self.username, item.author.name),
                                     response)
        except (AttributeError, praw.errors.PRAWException):
            pass

    def get_submission_by_id(self, sub_id: str) -> praw.objects.Submission:
        """Given a submission ID, load the actual submission object.

        Unused currently.

        :param sub_id: The submission ID
        :return:
        """
        url = 'https://www.reddit.com/r/{0}/comments/{1}/_/'.format(self.options['subreddit'], sub_id)
        return self.reddit.get_submission(url=url)

    def load_plugins(self) -> None:
        """Load all plugins from the plugins directory.

        In order for a module to be interpreted as a plugin, it must
        define __plugin__ as the plugin class somewhere in the module.
        """
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
                self.log.info('Initializing plugin %s', plugin.__name__)
                try:
                    self.plugins.append(plugin(**self.options))
                except Exception:
                    self.log.warning('Could not initialize plugin %s', plugin.__name__)

    def login(self) -> None:
        """Log into required services, like Reddit."""
        self.log.info('Logging into Reddit...')
        self.reddit = praw.Reddit(user_agent=self.options['useragent'])
        if self.use_oauth:
            self.oauth_authorize()
        else:
            self.username = self.options['reddit_user']
            self.reddit.login(username=self.username,
                              password=self.options['reddit_password'])
        self.sr = self.reddit.get_subreddit(self.options['subreddit'])

    def oauth_authorize(self):
        oauth = self.options['reddit_oauth']
        self.reddit.set_oauth_app_info(client_id=oauth['client_id'],
                                       client_secret=oauth['client_secret'],
                                       redirect_uri=oauth['redirect_uri'])
        self.access_information = {
            'access_token': oauth['access_token'],
            'refresh_token': oauth['refresh_token'],
            'scope': set(oauth['scope'])
        }
        self.oauth_refresh()
        self.username = self.reddit.get_me().name
        self.options['reddit_user'] = self.username

    def oauth_refresh(self):
        self.access_information = self.reddit.refresh_access_information(
            refresh_token=self.access_information['refresh_token'])

    def process_submission(self, submission: praw.objects.Submission) -> None:
        """Process a single submission, replying with a mirror if needed.

        :param submission: The Reddit submission to process.
        """
        self.log.debug('Processing submission\n'
                       '        permalink:%s\n'
                       '        url:      %s',
                       submission.permalink, submission.url)
        if any(comment.author.name == self.username
               for comment in submission.comments if comment.author):
            self.log.debug('Have already commented here--moving on.')
            return

        import_results = self.call_plugin_function('import_submission', submission=submission)
        if not any(import_results):
            self.log.debug('No processing done on "%s"', submission.url)
            return
        self.log.info('\n\nImported data from submission "%s"', submission.url)
        export_table = []
        import_info = None
        for import_info in filter(None, import_results):
            self.log.debug('Import info: %s', str(import_results))
            # export_results.append((import_info.get('importer_display', ''),
            export_results = self.call_plugin_function('export_submission', **import_info)
            if not any(export_results):
                continue
            importer_display = import_info.get('importer_display', {})
            export_table.append((importer_display, export_results, import_info))

        if not any(export_table):
            self.log.warning('Imports done, but no exports.')
            return

        links_display_parts = []
        for importer_display, export_results, _ in export_table:
            links_display_parts.append(importer_display.get('header', ''))
            for export_result in export_results:
                links_display_parts.append(export_result.get('link_display', ''))
            links_display_parts.append(importer_display.get('footer', ''))
        if not links_display_parts:
            self.log.warning('Exports done, but no links')
            return
        links_display = ''.join(links_display_parts)

        if self.use_mako:
            text = self.mako_template.render(
                submission=submission,
                links=links_display,
                links_parts=links_display_parts,
                import_info=import_info,
                export_table=export_table,
                **self.options)
        else:
            text = self.options.get('post_template',
                                    '{links}\n\n---\n^(Lapis Mirror {version})').format(
                links=links_display, **self.options)
        try:
            comment = submission.add_comment(text)
            self.log.info('Replied comment to %s', submission.permalink)
            self.sticky_comment(comment)
        except Exception:
            self.log.error('Had an error posting to Reddit! Attempting cleanup:\n%s', traceback.format_exc())
            try:
                for _, export_results, _ in export_table:
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

    def scan_submissions(self, delay: bool=False) -> None:
        """Scan the most recent submissions continually.

        :param delay: Whether to delay in-between each submission scanned.
        """
        done = []
        while True:
            if self.options.get('forward_replies'):
                for item in self.reddit.get_unread():
                    self.forward_reply(item)
            for submission in self.sr.get_new(limit=self.options.get('scan_limit', 50)):
                try:
                    if submission.id not in done:
                        self.process_submission(submission)
                except Exception:
                    self.log.error('Ran into error on submission %d' % submission.id)
                done.append(submission.id)
                if delay:
                    input()
            # self.log.debug('Waiting before next check')
            time.sleep(self.options.get('delay_interval', 30))
            if self.use_oauth:
                self.oauth_refresh()

    def sticky_comment(self, comment) -> bool:
        """Attempt to sticky a comment, failing silently.

        :return: Whether the sticky was successful.

        """
        obj = comment.reddit_session
        if obj.has_scope('modposts'):
            obj._use_oauth = True

        url = obj.config['distinguish']
        data = {'id': comment.fullname,
                'how': 'yes',
                'sticky': True}

        try:
            obj.request_json(url, data=data)
        except Exception:
            return False
        finally:
            obj._use_oauth = False

        self.log.debug('Successfully stickied comment: %s', comment.permalink)
        return True

    def verify_options(self) -> None:
        """Ensure that the provided options supply us with enough information."""
        if 'version' not in self.options:
            self.options['version'] = __version__
        if 'subreddit' not in self.options:
            raise LapisError('You must define a subreddit!')
        if 'reddit_oauth' in self.options:
            oauth = self.options['reddit_oauth']
            if not all(oauth.get(k)
                       for k in ('client_id',
                                 'client_secret',
                                 'redirect_uri',
                                 'access_token',
                                 'refresh_token',
                                 'scope')):
                raise LapisError('You are missing a reddit oauth option!')
            self.use_oauth = True
        else:
            if 'reddit_user' not in self.options:
                raise LapisError('You must define a user!')
            if 'reddit_password' not in self.options:
                raise LapisError('You must define a password!')
        if 'maintainer' not in self.options:
            raise LapisError('You must define a maintainer!')
        if 'post_template_file' in self.options:
            if 'post_template' in self.options:
                raise LapisError('Both a template file and template field were provided!')
            template_name = os.path.join(get_script_dir(), self.options['post_template_file'])
            if not os.path.isfile(template_name):
                raise LapisError('A template file was specified, but the file does not exist!')
            self.use_mako = True
            self.mako_template = Template(filename=template_name)

        self.options['useragent'] = self.options.get(
            'useragent', '{name}/{version} by {maintainer}'
        ).format(name='LapisMirror', **self.options)


def get_script_dir():
    """Try to reliably get the directory of the current script."""
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
        except LapisError:
            # LapisError happens when there's something configured wrong,
            # or a critical error occurs. We should leave the program.
            break
        except Exception:
            lapis.log.error('Error while scanning submission! %s', traceback.format_exc())
            time.sleep(10)
            lapis = LapisLazuli(**config)


if __name__ == '__main__':
    main()

# END OF LINE.
