# coding: utf-8

MESSAGE_DELIMITER = '\r\n'

LINE_DELIMITER = '\\n'
LINE_DELIMITER_LENGTH = len(LINE_DELIMITER)

KNOWN_COMMANDS = [
    '?', 'alias', 'ban', 'channel', 'chat', 'console',
    'del', 'difficulty', 'exit', 'extraocclusion', 'f', 'file',
    'help', 'history', 'host', 'kick', 'kick#', 'maxping',
    'mission', 'mp_dotrange', 'param', 'server', 'set', 'show',
    'socket', 'speedbar', 'timeout', 'tod', 'user', 'GC',
]

CHAT_SENDER_SERVER = 'Server'
CHAT_SENDER_SYSTEM = '---'
CHAT_MESSAGE_MAX_LENGTH = 80
