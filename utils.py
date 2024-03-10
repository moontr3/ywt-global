from typing import *

import datetime
import time
import random


# functions

def datetime_to_week(
    date:datetime.datetime, weekday:int=None,
    year:int=1970, month:int=3
) -> datetime.datetime:
    '''
    Converts a datetime object to a datetime with weeks instead
    of days and a preset year and a month for easier work with weekdays.
    '''
    if weekday == None:
        weekday = date.weekday()

    return datetime.datetime(
        year=year, month=month,
        day=weekday+1, hour=date.hour,
        minute=date.minute, second=date.second,
        microsecond=date.microsecond
    )

def int_to_script(number:int, superscript:bool=True) -> str:
    '''
    Converts an integer either to a superscript or a subscript string.
    '''
    data = '⁰¹²³⁴⁵⁶⁷⁸⁹' if superscript else '₀₁₂₃₄₅₆₇₈₉'
    string = ''.join(data[int(i)] for i in str(number))
    return string

def str_to_superscript(string:str) -> str:
    '''
    Converts a string to a string with superscript letters.
    '''
    string = str(string)
    replace_from = 'ABDEGHIJKLMNOPRTUVWabcdefghijklmnoprstuvwxyz+-=()0123456789.'
    replace_to =   'ᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵀᵁⱽᵂᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ⁺⁻⁼⁽⁾⁰¹²³⁴⁵⁶⁷⁸⁹·'

    for a, b in list(zip(replace_from, replace_to)):
        string = string.replace(a,b)
        
    return string

def shorten_time(seconds:int) -> str:
    '''
    Formats the amount of seconds into a neat string.
    '''
    if seconds > 60*60*24:
        return f'{int(seconds/60/60/24)}д. {int(60/60)%60}ч.'
    elif seconds > 60*60:
        return f'{int(seconds/60/60)}ч. {int(seconds/60)%60}м.'
    elif seconds > 60:
        return f'{int(seconds/60)} мин.'
    else:
        return f'{int(seconds)} сек.'
    
def shorten_string(string:str, max_chars:int=50, remove_newlines:bool=True) -> str:
    '''
    Strips the string.
    '''
    dots = False
    
    if len(string) > max_chars:
        dots = True
        string = string[:max_chars]
    
    if remove_newlines and '\n' in string:
        dots = True
        string = string.split('\n')[0]

    return string+('...' if dots else '')

    
def shorten_date(date:datetime.datetime) -> str:
    wd = weekday(date.weekday(), short=True)
    return f'{wd}, {date.day}'

def weekday(index, short=False, form=False) -> str:
    '''
    Returns a string representation of a weekday index (0-6 cuz index).
    '''
    if short:
        target = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    elif form:
        target = ['Понедельник', 'Вторник', 'Среду', 'Четверг', 'Пятницу', 'Субботу', 'Воскресенье']
    else:
        target = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    return target[index]

def month(index, short=False, form=False) -> str:
    '''
    Returns a string representation of a month number (1-12).
    '''
    if short:
        target = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
    elif form:
        target = ['Января','Февраля','Марта','Апреля','Мая','Июня','Июля','Августа','Сентября','Октября','Ноября','Декабря']
    else:
        target = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']
    return target[index-1]


def rand_id(k:int=4) -> str:
    '''
    Generates a random unique (probably) hexadecimal string that can be used as an ID.
    '''
    timestamp = str(int(time.time())) # unique timestamp that changes every second and never repeats after
    random_part = "".join(random.choices('0123456789', k=k)) # randomly generated string to add
                                                             # after the timestamp
    string = hex(int(timestamp+random_part))[2:] # converting the number to hex to make it shorter
    return string

def to_td(target_time: datetime.datetime) -> int:
    '''
    Converts the datetime object into an amount of seconds elapsed
    from the beginning of the day.
    '''
    return target_time.hour*60*60 + target_time.minute*60 + target_time.second