
# WARN i hate object oriented programming

from typing import *

from aiogram import types, Dispatcher, Bot, F
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio

import os
from dotenv import load_dotenv

import json
import utils
import api
import random
from log import *

import threading

# loading objects

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(TOKEN, parse_mode='html')
dp = Dispatcher()

mg = api.Manager(
    config.LESSONS_FILE, config.DB_FILE
)


# functions

def get_schedule_weekday_text(day:api.Day) -> str:
    '''
    Converts the `Day` object to a human-readable
    formatted string.
    '''
    out = [
        f'{i.start_time.hour}:{i.start_time.minute:0>2}-'\
        f'{i.end_time.hour}:{i.end_time.minute:0>2}  •  '\
        f'<b>{mg.lessons[i.name].name}</b> '\
        f'<i>({", ".join(l.room for l in mg.lessons[i.name].teachers)})</i>'
        for i in day.events if not i.is_break and i.name != None
    ]
    return '\n'.join(out)


def get_summary_text(day:api.Day, timedata:api.Time) -> str:
    '''
    Returns the text that is supposed to be shown when the summary
    command is sent.

    Essentially the same as `get_schedule_weekday_text`, but
    also includes the homework.
    '''
    out = []

    for index, i in enumerate(day.events):
        if i.is_break or i.name == None:
            continue

        # symbol
        if not timedata.is_school:
            symbol = ''
        elif timedata.event.is_break:
            symbol = '▹' if index-1 == timedata.event_index else ' '
        else:
            symbol = '▸' if index == timedata.event_index else ' '

        # text
        out.append(
            f'<code>{symbol}</code> '+\
            f'{i.start_time.hour}:{i.start_time.minute:0>2}-'\
            f'{i.end_time.hour}:{i.end_time.minute:0>2}  •  '\
            f'<b>{mg.lessons[i.name].name}</b> '\
            f'<i>({", ".join(l.room for l in mg.lessons[i.name].teachers)})</i>'
        )
        # todo homework here!!

    return '\n'.join(out)


def get_time_summary_text(timedata: api.Time, time_until_next_event:int) -> str:
    '''
    Converts the `Time` object to a string.
    '''
    timestr = f'{timedata.time.hour}:{timedata.time.minute:0>2}:{timedata.time.second:0>2}'
    datestr = f'{timedata.time.day} {utils.month(timedata.time.month, form=True).lower()}'
    out = f'⌚ Сейчас <b>{timestr}, {utils.weekday(timedata.weekday)}, {datestr}</b>\n'

    short_time = utils.shorten_time(time_until_next_event)
    if not timedata.is_school:
        out += f'⌛ Школа начнётся через <b>{short_time}</b>'
    else:
        event_type = 'перемена' if timedata.event.is_break else 'урок'
        out += f'⌛ Идёт <b>{timedata.event_number} {event_type}</b>'\
            f' ({timedata.event.length} мин.)  •  <i>TA {short_time}</i>'
        
    return out+'\n'


# commands

@dp.message(Command(commands=['start', 'help']))
async def cmd_start(msg: types.Message):
    '''
    Help command.
    '''
    # preparing
    check = mg.check(msg.from_user)
    if check:
        await msg.reply(f"❌ {check}")
        return

    log(f'{msg.from_user.full_name} ({msg.from_user.id}) started bot / requested help')

    # composing message
    phrase = random.choice(config.GREETING_PHRASES)
    out = f'🎉 <b>{phrase}</b>'

    # sending
    await msg.reply(out)



@dp.message(Command('summary'))
async def cmd_summary(msg: types.Message):
    '''
    Shows the summary - the schedule for the next lessons, homework
    info, current time info and some more stuff.
    '''
    # preparing
    check = mg.check(msg.from_user)
    if check:
        await msg.reply(f"❌ {check}")
        return

    log(f'{msg.from_user.full_name} ({msg.from_user.id}) requested summary')
    weekday, weekday_index = mg.get_summary()
    cur_time = api.Time(weekday, weekday_index)

    if cur_time.is_school:
        time_until_next_event = cur_time.time_remaining
    else:
        current_time = utils.datetime_to_week(datetime.datetime.now())
        next_lesson_time = utils.datetime_to_week(weekday.begin_time, weekday_index)
        
        # making sure that the next lesson comes after the current time
        if (next_lesson_time-current_time).total_seconds() < 0:
            next_lesson_time += datetime.timedelta(days=7)
        
        time_until_next_event = (next_lesson_time-current_time).total_seconds()

    # composing message
    out = get_time_summary_text(cur_time, int(time_until_next_event))

    out += f'<code>_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _</code>\n'
    out += f'<code>¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯</code>\n'
    out += f'📜 Расписание на <b>{utils.weekday(weekday_index, form=True).lower()}</b>:\n\n'
    out += get_summary_text(weekday, cur_time)

    # sending
    await msg.reply(out)



@dp.message(Command('schedule'))
async def cmd_schedule(msg: types.Message):
    '''
    Shows the schedule for each available weekday
    '''
    # preparing
    check = mg.check(msg.from_user)
    if check:
        await msg.reply(f"❌ {check}")
        return

    log(f'{msg.from_user.full_name} ({msg.from_user.id}) requested schedule')

    # creating keyboard
    kb = InlineKeyboardBuilder()
    for i in mg.available_days:
        kb.add(types.InlineKeyboardButton(
            text=utils.weekday(i, short=True), callback_data=f'schedule_{i}'
        ))

    # sending
    out = f'📪 Выберите день недели для отображения расписания'
    await msg.reply(out, reply_markup=kb.as_markup())



@dp.message(Command('subject'))
async def cmd_subject(msg: types.Message):
    '''
    Shows the info about a specific subject
    '''
    # preparing
    check = mg.check(msg.from_user)
    if check:
        await msg.reply(f"❌ {check}")
        return

    log(f'{msg.from_user.full_name} ({msg.from_user.id}) requested subject')

    # creating keyboard
    kb = InlineKeyboardBuilder()
    index = 0
    for i in mg.lessons:
        i = mg.lessons[i]
        btn = types.InlineKeyboardButton(
            text=i.name, callback_data=f'subject_{i.id}'
        )
        if index >= 2:
            index = 0
            kb.add(btn)
        else:
            index += 1
            kb.row(btn)

    # sending
    out = f'📪 Выберите предмет'
    await msg.reply(out, reply_markup=kb.as_markup())


# callbacks

@dp.callback_query(F.data.startswith('schedule_'))
async def inline_schedule(call: types.CallbackQuery):
    '''
    Schedule info callback
    '''
    # preparing
    check = mg.check(call.from_user)
    if check:
        await call.answer(f"❌ {check}")
        return

    weekday = int(call.data.removeprefix('schedule_'))
    log(f'{call.from_user.full_name} ({call.from_user.id}) requested schedule for {weekday}')

    # no lessons on such day
    if weekday not in mg.available_days:
        await call.answer(
            f'❌ Нет уроков на {utils.weekday(weekday, form=True)}!',
            show_alert=True
        )
        return

    data = mg.schedule[weekday]

    # composing message
    out = f'📜 Расписание на <b>{utils.weekday(weekday, form=True).lower()}</b>:\n'
    out += f'<code>_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _</code>\n'
    out += f'<code>¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯</code>\n'
    out += get_schedule_weekday_text(data)

    # creating keyboard
    kb = InlineKeyboardBuilder()
    for i in mg.available_days:
        kb.add(types.InlineKeyboardButton(
            text=utils.weekday(i, short=True),
            callback_data=f'schedule_{i}' if i != weekday else 'noop'
        ))

    # sending
    await call.message.edit_text(out, reply_markup=kb.as_markup())
    await call.answer()

    

@dp.callback_query(F.data.startswith('subject_'))
async def inline_subject(call: types.CallbackQuery):
    '''
    Subject info callback
    '''
    # preparing
    check = mg.check(call.from_user)
    if check:
        await call.answer(f"❌ {check}")
        return

    subject = call.data.removeprefix('subject_')
    log(f'{call.from_user.full_name} ({call.from_user.id}) requбested subject info for {subject}')

    data = mg.lessons[subject]
    occurences = mg.occurences(subject)
    joined_occurences = {}
    for i in occurences:
        if i[0] not in joined_occurences:
            joined_occurences[i[0]] = []
        joined_occurences[i[0]].append(i[1])

    # composing message
    out = f'📚 <b>{data.name}</b>\n'
    out += f'<code>_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _</code>\n'
    out += f'<code>¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯</code>\n'

    # times
    if len(occurences) > 0:
        out += f'📑 Всего <b>{len(occurences)}</b> ур. в неделю:\n'
        for i in joined_occurences:
            out += f'•  Стоит {", ".join([f"<b>{k+1}</b>" for k in joined_occurences[i]])} '\
                f'уроком в <b>{utils.weekday(i, form=True).lower()}</b>\n'
        out += '\n'
    else:
        out += f'📑 <i>Нет уроков</i>\n\n'

    # teachers
    out += '👩‍🏫 Учителя/кабинеты:\n'
    for i in data.teachers:
        out += f'•  <b>{i.name}</b> <i>({i.room})</i>\n'
    out += '\n' 

    # todo: homework here !!

    # sending
    await call.message.answer(out)
    await call.answer()


@dp.callback_query(F.data == 'noop')
async def noop_callback(call: types.CallbackQuery):
    '''
    Does literally nothing
    '''
    await call.answer()


# starting bot

log('Started polling...')
asyncio.run(dp.start_polling(bot))