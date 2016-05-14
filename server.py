#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import telepot
import logging
from logging import StreamHandler, Formatter
from flask import Flask, request

# Replace 0 with your ingress chat id.
TELEGRAM_INGRESS_CHAT_ID = 0

# Replace '' with your telegram bot token
TELEGRAM_BOT_TOKEN = ''

app = Flask(__name__)

trigger = {
    u'<PORTAL_NAME>': '<TELEGRAM_USER_ID>',
}

def _parse(lines):
    """
    Input: lines =
    [
        u'Agent Name:dm4Faction:EnlightenedCurrent Level:L8',
        u'DAMAGE REPORT',
        u'不設限',
        u'No. 200, Jingye 2nd Road, Zhongshan District, Taipei City, Taiwan 104',
        u'DAMAGE:1 Link destroyed by Questting at 10:41 hrs GMT6 Resonators remaining on this Portal.',
        u'STATUS:Level 4Health: 87%Owner: dm4',
        u'捷運劍南路站',
        u'Jiannan road station, Zhongshan District, Taipei City, Taiwan 104',
        u'LINKS DESTROYED',
        u'不設限: No. 200, Jingye 2nd Road, Zhongshan District, Taipei City, Taiwan 104',
        u'Wego Motel NeiHu: No. 11, Jìngyè 3rd Road, Zhongshan District, Taipei City, Taiwan 104',
        u'DAMAGE:2 Links destroyed by Questting at 10:41 hrs GMT1 Resonator remaining on this Portal.',
        u'STATUS:Level 1Health: 6%Owner: CynthiaCC',
    ]

    Return: (agent, portals) =
    (
        {
            'name': 'dm4',
            'level': '8',
        },
        [
            {
                'name': '不設限',
                'level': '4',
                'health': '87',
                'remain': '6',
                'attacker': 'Questting',
                'owner': 'dm4',
            },
            {
                'name': '捷運劍南路站',
                'level': '1',
                'health': '6',
                'remain': '1',
                'attacker': 'Questting',
                'owner': 'CynthiaCC',
                'links': ['不設限', 'Wego Motel NeiHu']
            },
        ],
    )
    """
    agent = {}
    portals = []

    # Parse message.
    line = lines.pop(0)
    m = re.match('Agent Name:(.*)Faction:(.*)Current Level:L(\d*)', line)
    if m:
        agent['name'] = m.group(1)
        agent['level'] = m.group(3)

    line = lines.pop(0)
    if line != 'DAMAGE REPORT':
        app.logger.warning('No DAMAGE REPORT?')
        return (agent, portals)

    while len(lines) > 0:
        portal = {}
        portal['name'] = lines.pop(0)
        portal['address'] = lines.pop(0)
        if lines[0] == 'LINK DESTROYED' or lines[0] == 'LINKS DESTROYED':
            lines.pop(0)
            portal['links'] = []
            while lines[0][:7] != 'DAMAGE:':
                line = lines.pop(0)
                link_portal = line.split(':')[0]
                portal['links'].append(link_portal)

        # DAMAGE:
        line = lines.pop(0)
        m = re.match('DAMAGE:(.* destroyed by (.*) at .*GMT)(.*)', line)
        if m:
            portal['attacker'] = m.group(2)
            remain_line = m.group(3)
        portal['remain'] = '0'
        m = re.match('(\d+) Resonators? remaining on this Portal.', remain_line)
        if m:
            portal['remain'] = m.group(1)

        # STATUS:
        line = lines.pop(0)
        m = re.match('STATUS:Level (\d*)Health: (\d*)%Owner: (.*)', line)
        if m:
            portal['level'] = m.group(1)
            portal['health'] = m.group(2)
            portal['owner'] = m.group(3)

        # Add portal.
        portals.append(portal)

    return (agent, portals)

@app.route('/', methods=['POST'])
def index():
    # Initialize bot.
    bot = telepot.Bot(TELEGRAM_BOT_TOKEN)

    # Get parameters.
    body = request.form.get('body', '')
    lines = list(filter(lambda x: x != '', body.split('\n')))

    # Logging.
    app.logger.warning('LINES:\n' + '\n'.join(lines))

    # Check body.
    if body == '':
        return 'Fail!'

    # Parse lines.
    (agent, portals) = _parse(lines)

    # Build message.
    for portal in portals:
        message = u'%s (L%s) 的 %s (L%s, HP %s%%, 剩 %s 隻腳) 被 %s 打啦！' \
            % (agent['name'], agent['level'], portal['name'], portal['level'],
               portal['health'], portal['remain'], portal['attacker'])
        if 'links' in portal:
            message += u'到 %s 的連結被破壞了！\n' % (', '.join(portal['links']))
        app.logger.warning(message)

        # Check if triggered.
        if portal['name'] in trigger:
            app.logger.warning(u'Trigger %s: %s' % (portal['name'], trigger[portal['name']]))
            bot.sendMessage(TELEGRAM_INGRESS_CHAT_ID, '@%s: %s' % (trigger[portal['name']], message))

    return "Done!"

if __name__ == "__main__":
    handler = StreamHandler()
    handler.setFormatter(Formatter(
        '[%(levelname)s] [%(asctime)s] %(pathname)s:%(lineno)d - %(message)s',
        '%Y-%m-%d %H:%M:%S'
    ))
    app.logger.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)
    app.run(port=3001)
