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
ADMINS = [1365781815] # list of telegram user IDs that are admins in this bot
                      # the default one is me remove this please