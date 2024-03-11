LOG_FILE = 'log.txt'          # path to log file
LESSONS_FILE = 'lessons.json' # path to the file with lesson information
DB_FILE = 'data.json'         # path to database file

GREETING_PHRASES = [
    'С Новым Годом!',
    'С 9 мая!',
    'С 8 марта!',
    'С Масленицей!',
    'С Рождеством!',
    'С Пасхой!',
    'С 1 сентября!',
    'С Днем Рождения!',
    'С Днем России!',
    'С Днем Пива!',
    'С Днем Алкоголика!',
    'С кибиди доп доп ес ес'
] # a list of phrases to choose from when displaying the /help command.

USE_WHITELIST = False # if True changes the blacklist to become a whitelist
USE_WRITE_WHITELIST = False # if True changes the write blacklist to become a whitelist
ADMINS = [1365781815] # list of telegram user IDs that are admins in this bot
                      # the default one is me remove this please

IMAGE_WATERMARK_TEXT = 'https://github.com/moontr3/ywt-global' # watermark to put on uploaded attachments

HELP_TEXT = '''\
<b>/help</b> - список команд
<b>/summary</b> - посмотреть краткое расписание и ДЗ
<b>/homework</b> - посмотреть или изменить записанное ДЗ
<b>/subject</b> - посмотреть информацию о предмете
<b>/schedule</b> - посмотреть расписание уроков на любой день
<b>/eco</b> - открыть меню экономики
'''

DEFAULT_BALANCE = 0 # default economy balance
CURRENCY = '🍆' # currency symbol
DAILY_REWARD_RANGE = [25,50] # range between which numbers the resulting daily reward will be
DAILY_REWARD_TIMEOUT = 6*60*60 # daily reward timeout in seconds
