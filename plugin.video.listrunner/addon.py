# -*- coding: utf-8 -*-

"""
    Listrunner Add-on
    Author: Twilight0

        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import re
from resources.lib import ordereddict, client, youtube, cache, control
from resources.lib import syshandle, sysurl, action, params

try:
    import YDStreamExtractor
except ImportError:
    pass

try:
    import urlresolver
except ImportError:
    pass


def constructor():

    _list_ = [] ;  groups = []

    if control.setting('local_or_remote') == '0':
        try:
            with open (control.setting('local')) as _file_:
                text = _file_.read()
                _file_.close()
        except IOError:
            return 'null'
    elif control.setting('local_or_remote') == '2':
        return 'Youtube'
    else:
        try:
            text = client.request(control.setting('remote'))
            if text is None:
                raise ValueError
        except ValueError:
            text = client.request(control.setting('remote'), close=False)
            if text is None:
                return 'null'

    result = text.replace('\r\n', '\n')
    items = re.compile('EXTINF:(-?\d*)(,| |.*?)\n#', re.U + re.S).findall(result + '\n#')

    for duration, item in items:

        title = re.findall('[^\d*?],(.*?)\\n', ' ' + item, re.U)[0]
        link = re.findall('\\n(.*?)$', item, re.U)[0]

        if not control.condVisibility('System.HasAddon(script.module.urlresolver)'):
            link = link.replace('https://www.youtube.com/watch?v=', 'plugin://plugin.video.youtube/play/?video_id=')
            link = link.replace('https://youtu.be/', 'plugin://plugin.video.youtube/play/?video_id=')

        duration = int(duration)

        if 'tvg-logo' in item:
            icon = re.findall('tvg-logo="(.*?)"', item, re.U)[0]
        elif 'icon' in item:
            icon = re.findall('icon="(.*?)"', item, re.U)[0]
        elif 'image' in item:
            icon = re.findall('image="(.*?)"', item, re.U)[0]
        else:
            icon = control.addonInfo('icon')

        if 'group-title' in item:
            group = re.findall('group-title="(.*?)"', item, re.U)[0]
        else:
            group = ''

        data = ({'title': title.decode('utf-8'), 'image': icon, 'group': 'NULL' if group == '' else group.decode('utf-8'), 'url': link, 'duration': duration if duration > 0 else None})
        _list_.append(data)
        groups.append(group.decode('utf-8'))

    trimmed_groups = list(ordereddict.OrderedDict.fromkeys(groups))

    trimmed_groups.sort()

    if len(trimmed_groups) == 1:
        control.setSetting('group', 'ALL')

    if not text.startswith('#EXTM3U'):
        return
    else:
        return _list_, trimmed_groups


def switcher():

    groups = [control.lang(30016)] + constructor()[1]

    choices = control.dialog.select(heading=control.lang(30017), list=groups)

    if choices == 0:
        control.setSetting('group', 'ALL')
        control.execute('Dialog.Close(busydialog)')
        control.sleep(50)
        control.execute('Container.Refresh')
    elif choices <= len(groups) and not choices == -1:
        control.setSetting('group', (groups.pop(choices)))
        control.execute('Dialog.Close(busydialog)')
        control.sleep(50)
        control.execute('Container.Refresh')
    else:
        control.execute('Dialog.Close(busydialog)')
        control.dialog.notification(heading=control.addonInfo('name'), message=control.lang(30019), icon=control.addonInfo('icon'), sound=False)


def nullify(_id_):

    null = [
        {
            'title': control.lang(_id_),
            'image': control.join(control.addonmedia('null.png')),
            'url': sysurl
        }
    ]

    return null


def main_menu():

    _list_ = []

    root_menu = [
        {
            'title': control.lang(30011),
            'image': control.join(control.addonmedia('settings.png')),
            'url': '{0}?action={1}'.format(sysurl, 'settings')
        }
        ,
        {
            'title': control.lang(30015).format(control.lang(30016) if control.setting('group') == 'ALL' else control.setting('group').decode('utf-8')),
            'image': control.join(control.addonmedia('switcher.png')),
            'url': '{0}?action={1}'.format(sysurl, 'switcher')
        }
    ]

    try:
        if constructor() == 'Youtube':
            if 'playlist?list=' in control.setting('youtube_url'):
                _items_ = root_menu + cache.get(youtube.youtube(key='AIzaSyA8k1OyLGf03HBNl0byD511jr9cFWo2GR4').playlist,
                                                int(control.setting('caching')) if int(control.setting('caching')) > 0 else 0,
                                                control.setting('youtube_url').partition('list=')[2])
                del _items_[1]
            elif not bool(control.setting('youtube_url')):
                raise TypeError
            else:
                raise ValueError
        elif constructor() == 'null':
            raise TypeError
        elif not constructor()[0] == []:
            if len(constructor()[1]) == 1:
                del root_menu[1]
            if control.setting('group') not in constructor()[1]:
                control.setSetting('group', 'ALL')
            filtered = [item for item in constructor()[0] if any(item['group'] == selected for selected in [control.setting('group').decode('utf-8')])] if not control.setting('group') == 'ALL' else constructor()[0]
            _items_ = root_menu + filtered
        else:
            raise ValueError
    except ValueError:
        _items_ = root_menu + nullify(30013)
        del _items_[1]
    except TypeError:
        _items_ = root_menu + nullify(30026)
        del _items_[1]

    for item in _items_:

        li = control.item(label=item['title'])
        li.setInfo('video', {'title': item['title']})
        li.setArt({'icon': item['image'], 'thumb': item['image'], 'fanart': control.addonInfo('fanart')})
        li.setProperty('IsPlayable', 'true')
        li.addContextMenuItems([(control.lang(30012), 'RunPlugin({0}?action=refresh)'.format(sysurl))])
        _url_ = '{0}?action=play&url={1}'.format(sysurl, item['url'])
        isFolder = False
        if control.setting('youtube') == 'true' and item['url'].startswith('plugin://plugin.video.youtube/play/?video_id='):
            _url_ = '{0}?action=play&url={1}'.format(sysurl, item['url'])
        if control.setting('youtube') == 'false' and item['url'].startswith('plugin://plugin.video.youtube/play/?video_id='):
            _url_ = item['url']
        if item['url'].startswith('plugin://'):
            _url_ = item['url']
        if item['url'].endswith(('settings', 'switcher')):
            li.setProperty('IsPlayable', 'false')
        _list_.append((_url_, li, isFolder))

    control.addItems(syshandle, _list_)
    control.directory(syshandle, cacheToDisc=True)


def play_item(path):

    li = control.item(path=path)
    control.resolve(syshandle, True, listitem=li)


if action is None:

    main_menu()

elif action == 'play':

    if params['url'].startswith('plugin://plugin.video.youtube/play/?video_id='):
        control.execute('PlayMedia("{0}")'.format(params['url']))
    else:
        try:
            stream = YDStreamExtractor.getVideoInfo(params['url'])
            url = stream.streamURL()
            # title = stream.selectedStream()['title']
            # icon = stream.selectedStream()['thumbnail']
            play_item(url)
        except AttributeError:
            try:
                if urlresolver.HostedMediaFile(params['url']).valid_url():
                    url = urlresolver.resolve(params['url'])
                    play_item(url)
                else:
                    play_item(params['url'])
            except NameError:
                play_item(params['url'])
        except NameError:
            try:
                if urlresolver.HostedMediaFile(params['url']).valid_url():
                    url = urlresolver.resolve(params['url'])
                    play_item(url)
                else:
                    play_item(params['url'])
            except NameError:
                play_item(params['url'])

elif action == 'install_youtube-dl':

    if control.condVisibility('System.HasAddon(script.module.youtube.dl)'):
        control.infoDialog(control.lang(30030))
    else:
        control.execute('RunPlugin(plugin://script.module.youtube.dl)')

elif action == 'install_urlresolver':

    if control.condVisibility('System.HasAddon(script.module.urlresolver)'):
        control.infoDialog(control.lang(30031))
    else:
        control.execute('RunPlugin(plugin://script.module.urlresolver)')

elif action == 'settings':

    control.openSettings()

elif action == 'refresh':

    control.execute('Container.Refresh')

elif action == 'switcher':

    control.dialog.notification(heading=control.addonInfo('name'), message=control.lang(30020), time=1500, sound=False)
    control.execute('ActivateWindow(busydialog)')
    switcher()

elif action == 'cache_clear':

    if control.yesnoDialog(line1=control.lang(30028), line2='', line3=''):

        control.deleteFile(control.cacheFile)

    else:

        control.infoDialog(control.lang(30029))
