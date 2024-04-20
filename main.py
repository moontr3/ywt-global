
# WARN i hate object oriented programming

from typing import *

from aiogram import types, Dispatcher, Bot, F
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio

import os
from dotenv import load_dotenv

import time
import utils
import api
import random
from log import *

from PIL import Image, ImageDraw, ImageFont

# loading objects

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(TOKEN, parse_mode='html')
dp = Dispatcher()

mg = api.Manager(
    config.LESSONS_FILE, config.DB_FILE
)



# ---------------------------
# functions
# ---------------------------

def get_profile_text(user:api.User) -> str:
    '''
    Creates a stats message for a user
    '''
    out = f'👤 <b>{user.name}</b>\n'
    out += f'🏢 <code>[{user.company_handle}]</code> {user.company_name}\n'
    out += f'<code>_ _ _ _ _ _ _ _ _ _ _ _ _ _ _</code>\n'
    out += f'<code>¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯</code>\n'
    out += f'💵 Баланс: <b>{user.balance}{config.CURRENCY}</b>\n'

    return out


def get_stats_text(user:api.User) -> str:
    '''
    Creates a eco stats message
    '''
    out = f'👋 Привет, <b>{user.name}</b>!\n'   
    out += f'<code>_ _ _ _ _ _ _ _ _ _ _ _ _ _ _</code>\n'
    out += f'<code>¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯</code>\n'
    
    out += f'💵 Ваш баланс: <b>{user.balance}{config.CURRENCY}</b>\n'
    if time.time() >= user.daily_until:
        out += f'🎁 Ежедневная награда уже доступна!'
    else:
        out += f'🎁 Ежедневная награда через: <b>{utils.shorten_time(user.daily_until-time.time())}</b>'

    return out
    

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
    out = ''

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
        out += f'<code>{symbol}</code>'+\
            f'{i.start_time.hour}:{i.start_time.minute:0>2}-'\
            f'{i.end_time.hour}:{i.end_time.minute:0>2}  •  '\
            f'<b>{mg.lessons[i.name].name}</b> '\
            f'<i>({", ".join(l.room for l in mg.lessons[i.name].teachers)})</i>\n'

        hw = mg.get_homework(i.name)
        for x in hw:
            # not showing today's homework
            if datetime.date.fromtimestamp(x.written_at) == datetime.date.today():
                continue
            out += '<code>  </code>'+utils.hw_to_string(x, False)+'\n'

    return out


def get_time_summary_text(timedata: api.Time, time_until_next_event:int) -> str:
    '''
    Converts the `Time` object to a string.
    '''
    timestr = f'{timedata.time.hour}:{timedata.time.minute:0>2}:{timedata.time.second:0>2}'
    datestr = f'{timedata.time.day} {utils.month(timedata.time.month, form=True).lower()}'
    out = f'⌚ Сейчас <b>{timestr}, {utils.weekday(timedata.time.weekday())}, {datestr}</b>\n'

    short_time = utils.shorten_time(time_until_next_event)
    if not timedata.is_school:
        out += f'⌛ Школа начнётся через <b>{short_time}</b>'
    else:
        event_type = 'перемена' if timedata.event.is_break else 'урок'
        out += f'⌛ Идёт <b>{timedata.event_number} {event_type}</b>'\
            f' ({timedata.event.length} мин.)  •  <i>TA {short_time}</i>'
        
    return out+'\n'


def get_homework_text(hw: Dict[str, List[api.HomeworkEntry]]):
    '''
    Makes a neat string out of a dict with your homework.
    '''
    out = '📖 <b>Домашние задания:</b>\n'
    out += f'<code>_ _ _ _ _ _ _ _ _ _ _ _ _ _ _</code>\n'
    out += f'<code>¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯</code>\n'

    if not hw:
        out += '<i>Ничего не записано</i>'

    else:
        for k, i in hw.items():
            out += f'<b>{k}:</b>\n'
            for x in i:
                out += utils.hw_to_string(x, user=mg.get_user(x.written_by).name)+'\n'
            out += '\n'

    return out


def add_overlay(attachment:api.Attachment) -> str:
    '''
    Adds overlay to an attachment and returns the file path.
    '''
    log(f'Adding overlay to {attachment.id}')

    # applying overlay
    shadow_size = 80 # shadow vertical size in pixels
    written_at = datetime.datetime.fromtimestamp(attachment.written_at)
    lesson = mg.lessons[attachment.lesson]

    image = Image.open(attachment.filename).convert('RGBA')
    gradient = Image.open('assets/image_shadow.png').convert('RGBA')
    font = ImageFont.truetype('assets/regular.ttf', 16)
    bold_font = ImageFont.truetype('assets/bold.ttf', 16)

    gradient = gradient.resize((image.size[0], shadow_size))
    image.paste(gradient, (0, image.size[1]-shadow_size), gradient)
    draw = ImageDraw.Draw(image)

    # comment
    text = utils.shorten_string(attachment.comment)
    draw.text((10, image.size[1]-10), text, (255,255,255), bold_font, 'ld')
    # lesson name
    draw.text((10, image.size[1]-30), lesson.name, (255,255,255), font, 'ld')

    # watermark
    draw.text(
        (image.size[0]-10, image.size[1]-10),
        config.IMAGE_WATERMARK_TEXT, (255,255,255),
        font, 'rd'
    )
    # author
    user = mg.get_user(attachment.written_by)
    if user:
        user = utils.shorten_string(user.full_name, 25)
    else:
        user = f'ID: {attachment.written_by}'

    string = f'От {user}'\
        f' в {utils.shorten_date(written_at)}'
    draw.text(
        (image.size[0]-10, image.size[1]-30),
        string, (255,255,255),
        font, 'rd'
    )

    # saving the image
    if not os.path.exists('temp/'):
        os.mkdir('temp/')

    savefile = f'temp/{attachment.id}.png'
    image.save(savefile)
    image.close()

    return savefile


async def download_image(
    img_id:int, lesson:api.Lesson,
    comment:str, written_by:types.User
) -> str:
    '''
    Downloads an image via a Telegram attachment ID,
    adds a watermark and some info, saves it and returns
    the attachment ID. 
    '''
    id = utils.rand_id()
    log(f'Downloading attachment for {lesson.id} homework by {written_by.id}')
    
    # downloading file
    try:
        if not os.path.exists('attachments/'):
            os.mkdir('attachments/')

        file = await bot.get_file(img_id)
        extension = file.file_path.split('.')[-1]
        filepath = f'attachments/{id}.{extension}'

        await bot.download(img_id, filepath)

    except Exception as e:
        log(f'Error while downloading file: {e}', level=ERROR)
        return None

    # adding attachment
    mg.add_attachment(id, filepath, lesson.id, comment, time.time(), written_by.id)

    return id





# ---------------------------
# commands
# ---------------------------

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
    out = f'🎉 <b>{phrase}</b>\n\n'
    out += config.HELP_TEXT

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
    weekday: api.Day
    weekday_index: int
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

    out += f'<code>_ _ _ _ _ _ _ _ _ _ _ _ _ _ _</code>\n'
    out += f'<code>¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯</code>\n'
    out += f'📜 Расписание на <b>{utils.weekday(weekday_index, form=True).lower()}</b>:\n\n'
    out += get_summary_text(weekday, cur_time)
    
    # images
    kb = InlineKeyboardBuilder()

    for i in mg.attachments.values():
        if i.lesson not in weekday.lessons: continue
        # not showing today's homework
        if datetime.date.fromtimestamp(i.written_at) == datetime.date.today():
            continue
        # adding homework
        lesson = mg.lessons[i.lesson]
        kb.row(types.InlineKeyboardButton(
            text=f"📷 {lesson.short_name}: {i.comment}",
            callback_data=f'image_{i.id}'
        ))

    # sending
    await msg.reply(out, reply_markup=kb.as_markup())



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
    index = 3
    for i in mg.lessons:
        i = mg.lessons[i]
        btn = types.InlineKeyboardButton(
            text=i.name, callback_data=f'subject_{i.id}'
        )
        if index >= 2:
            index = 0
            kb.row(btn)
        else:
            index += 1
            kb.add(btn)

    # sending
    out = f'📪 Выберите предмет'
    await msg.reply(out, reply_markup=kb.as_markup())



@dp.message(Command('homework'))
async def cmd_homework(msg: types.Message):
    '''
    Shows the homework for all lessons
    '''
    # preparing
    check = mg.check(msg.from_user)
    if check:
        await msg.reply(f"❌ {check}")
        return

    log(f'{msg.from_user.full_name} ({msg.from_user.id}) requested homework list')

    # creating keyboard
    kb = InlineKeyboardBuilder()
    if mg.write_availability(msg.from_user.id):
        kb.add(types.InlineKeyboardButton(text="✏ Изменить", callback_data=f'hweditor'))

    # images
    for i in mg.attachments.values():
        lesson = mg.lessons[i.lesson]
        kb.row(types.InlineKeyboardButton(
            text=f"📷 {lesson.short_name}: {i.comment}",
            callback_data=f'image_{i.id}'
        ))

    # composing message
    data = mg.get_homework_dict()
    out = get_homework_text(data)

    # sending
    await msg.reply(out, reply_markup=kb.as_markup())





# ---------------------------
# admin shit
# ---------------------------

@dp.message(Command('reload'))
async def cmd_reload(msg: types.Message):
    '''
    Shows the basic user stats
    '''
    # preparing
    if msg.from_user.id not in config.ADMINS:
        return

    log(f'{msg.from_user.full_name} ({msg.from_user.id}) requested reload')

    mg.reload_db()

    # sending
    out = f'✅ Success!'
    await msg.reply(out)





# ---------------------------
# economy command
# ---------------------------

@dp.message(Command('search'))
async def cmd_find_user(msg: types.Message):
    '''
    Searches for user by company handle
    '''
    # preparing
    check = mg.check(msg.from_user, True)
    if check:
        await msg.reply(f"❌ {check}")
        return

    log(f'{msg.from_user.full_name} ({msg.from_user.id}) finding user')
    mg.set_state(msg.from_user.id, 'find_user')

    # composing message
    out = '🔍 Введите в чат того, кого вы хотите найти'

    # creating keyboard
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="❌ Отмена", callback_data=f'reset_state'))

    # sending
    await msg.reply(out, reply_markup=kb.as_markup())



@dp.message(Command('eco'))
async def cmd_eco(msg: types.Message):
    '''
    Shows the basic user stats
    '''
    # preparing
    check = mg.check(msg.from_user, True)
    if check:
        await msg.reply(f"❌ {check}")
        return

    log(f'{msg.from_user.full_name} ({msg.from_user.id}) requested eco')

    # composing message
    user = mg.get_user(msg.from_user.id)
    out = get_stats_text(user)

    # creating keyboard
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="🚽 Плот", callback_data=f'plot'))
    kb.add(types.InlineKeyboardButton(text="📊 Компания", callback_data=f'company'))
    kb.row(types.InlineKeyboardButton(text="🎁 Ежедневная награда", callback_data=f'daily'))

    # sending
    await msg.reply(out, reply_markup=kb.as_markup())



@dp.callback_query(F.data == 'eco')
async def inline_eco(call: types.CallbackQuery):
    '''
    Shows the basic user stats (inline)
    '''
    # preparing
    check = mg.check(call.from_user, True)
    if check:
        await call.answer(f"❌ {check}")
        return

    log(f'{call.from_user.full_name} ({call.from_user.id}) requested eco (inline)')

    # composing message
    user = mg.get_user(call.from_user.id)
    out = get_stats_text(user)

    # creating keyboard
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🚽 Плот", callback_data=f'plot'))
    kb.add(types.InlineKeyboardButton(text="📊 Компания", callback_data=f'company'))
    kb.row(types.InlineKeyboardButton(text="🎁 Ежедневная награда", callback_data=f'daily'))

    # sending
    await call.message.edit_text(out, reply_markup=kb.as_markup())
    await call.answer()




@dp.callback_query(F.data == 'company')
async def inline_company(call: types.CallbackQuery):
    '''
    Displays company info
    '''
    # preparing
    check = mg.check(call.from_user, True)
    if check:
        await call.answer(f"❌ {check}")
        return

    log(f'{call.from_user.full_name} ({call.from_user.id}) requested company info')
    user = mg.get_user(call.from_user.id)

    # composing message
    out = f'🏢 <b>{user.name}</b>, вы в офисе своей компании\n'\
        f'<b><code>[{user.company_handle}]</code> {user.company_name}</b>\n'
    out += f'<code>_ _ _ _ _ _ _ _ _ _ _ _ _ _ _</code>\n'
    out += f'<code>¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯</code>\n'

    # creating keyboard
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="⬅ Назад", callback_data=f'eco'))
    kb.row(types.InlineKeyboardButton(text="✏ Сменить имя", callback_data=f'edit_name'))
    kb.add(types.InlineKeyboardButton(text="✏ Сменить тэг", callback_data=f'edit_handle'))

    # sending
    await call.message.edit_text(out, reply_markup=kb.as_markup())
    await call.answer()



@dp.callback_query(F.data == 'plot')
async def inline_company(call: types.CallbackQuery):
    '''
    Displays company info
    '''
    # preparing
    check = mg.check(call.from_user, True)
    if check:
        await call.answer(f"❌ {check}")
        return

    log(f'{call.from_user.full_name} ({call.from_user.id}) requested plot info')
    user = mg.get_user(call.from_user.id)

    # composing message
    out = f'🚽 <b>{user.name}</b>, вы в своем подвале туалетов\n'\
        f'🧻 <b>У вас {user.max_slots} слотов</b>\n'
    out += f'<code>_ _ _ _ _ _ _ _ _ _ _ _ _ _ _</code>\n'
    out += f'<code>¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯</code>\n'
    for index, i in enumerate(user.slots):
        out += f'<code>{index+1}</code> '
        if i.toilet_data == None:
            out += '<i>Пустой слот</i>'
        
        out += '\n'

    # creating keyboard
    kb = InlineKeyboardBuilder()
    rownum = 0
    for index, i in enumerate(user.slots):
        if i.toilet_data == None:
            symbol = '➖'
        else:
            symbol = '❓'
        button = types.InlineKeyboardButton(text=f'{index+1} {symbol}', callback_data=f'slot_{index}')
            
        rownum += 1
        if rownum > 5:
            kb.row(button)
        else:
            kb.add(button)
    kb.row(types.InlineKeyboardButton(text="⬅ Назад", callback_data=f'eco'))

    # sending
    await call.message.edit_text(out, reply_markup=kb.as_markup())
    await call.answer()




@dp.callback_query(F.data == 'daily')
async def inline_daily(call: types.CallbackQuery):
    '''
    Collects daily reward
    '''
    # preparing
    check = mg.check(call.from_user, True)
    if check:
        await call.answer(f"❌ {check}")
        return

    log(f'{call.from_user.full_name} ({call.from_user.id}) collecting daily reward')
    user = mg.get_user(call.from_user.id)

    # composing message
    reward = mg.collect_daily(user.id)

    if reward == None:
        await call.answer('❌ Приходите за наградой через '\
                         f'{utils.shorten_time(user.daily_until-time.time())}!', True)
        return
    
    out = f'🎁 <b>{user.name}</b>, вы получили <b>{reward}{config.CURRENCY}</b>!\n\n'\
        f'Приходите через <b>{utils.shorten_time(config.DAILY_REWARD_TIMEOUT)}</b> за новой наградой!'

    # creating keyboard
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="⬅ Назад", callback_data=f'eco'))

    # sending
    await call.message.edit_text(out, reply_markup=kb.as_markup())
    await call.answer()




@dp.callback_query(F.data == 'edit_handle')
async def inline_edit_handle(call: types.CallbackQuery):
    '''
    Edits company handle
    '''
    # preparing
    check = mg.check(call.from_user, True)
    if check:
        await call.answer(f"❌ {check}")
        return

    log(f'{call.from_user.full_name} ({call.from_user.id}) editing company handle')
    user = mg.get_user(call.from_user.id)
    
    # checking availability
    if not user.handle_change_free and user.balance < config.HANDLE_CHANGE_COST:
        await call.answer(f'❌ Вам необходимо {config.HANDLE_CHANGE_COST}{config.CURRENCY}'\
            f' для изменения тэга!\n\nВаш баланс: {user.balance}{config.CURRENCY}', True)
        return
    
    mg.set_state(user.id, 'edit_handle')

    # composing message
    out = f'<b>{user.name}</b>, введите в чат новый тэг вашей компании.\n\n'\
        f'Текущий тэг: <b><code>{user.company_handle}</code></b>\n' + (
            f'<b>Цена изменения: {config.HANDLE_CHANGE_COST}{config.CURRENCY}</b>\n\n'\
            if not user.handle_change_free else\
            f'<b>Это изменение будет бесплатным. Потом - {config.HANDLE_CHANGE_COST}{config.CURRENCY}</b>\n\n'
        ) + f'<i>{config.HANDLE_MUST_CONTAIN_TEXT}</i>\n'\
        f'<i>Максимальное кол-во символов: <b>{config.HANDLE_MAX_LENGTH}</b></i>'

    # creating keyboard
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="❌ Отмена", callback_data=f'company'))

    # sending
    await call.message.edit_text(out, reply_markup=kb.as_markup())
    await call.answer()


@dp.callback_query(F.data == 'edit_name')
async def inline_edit_name(call: types.CallbackQuery):
    '''
    Edits company name
    '''
    # preparing
    check = mg.check(call.from_user, True)
    if check:
        await call.answer(f"❌ {check}")
        return

    log(f'{call.from_user.full_name} ({call.from_user.id}) editing company name')
    user = mg.get_user(call.from_user.id)
    mg.set_state(user.id, 'edit_name')

    # composing message
    out = f'<b>{user.name}</b>, введите в чат новое название вашей компании.\n\n'\
        f'Текущее имя: <b>{user.company_name}</b>\n\n'\
        f'<i>Максимальное кол-во символов: <b>{config.COMP_NAME_MAX_LENGTH}</b></i>'

    # creating keyboard
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="❌ Отмена", callback_data=f'company'))

    # sending
    await call.message.edit_text(out, reply_markup=kb.as_markup())
    await call.answer()



@dp.callback_query(F.data.startswith('profile_'))
async def inline_profile(call: types.CallbackQuery):
    '''
    Displays profile of a user
    '''
    # preparing
    check = mg.check(call.from_user, True)
    if check:
        await call.answer(f"❌ {check}")
        return

    user = mg.get_user(int(call.data.removeprefix('profile_')))
    log(f'{call.from_user.full_name} ({call.from_user.id}) requested profile info for {user.id}')

    # checking user
    if user == None:
        await call.answer('❌ Пользователь не найден', True)
        return

    # sending
    out = get_profile_text(user)
    await call.message.answer(out)
    await call.answer()




# ---------------------------
# callbacks
# ---------------------------

@dp.callback_query(F.data == 'homework')
async def inline_editor(call: types.CallbackQuery):
    '''
    Shows the homework for all lessons
    '''
    # preparing
    check = mg.check(call.from_user, True)
    if check:
        await call.answer(f"❌ {check}")
        return

    log(f'{call.from_user.full_name} ({call.from_user.id}) requested homework list (inline)')

    # creating keyboard
    kb = InlineKeyboardBuilder()
    if mg.write_availability(call.from_user.id):
        kb.add(types.InlineKeyboardButton(text="✏ Изменить", callback_data=f'hweditor'))

    # images
    for i in mg.attachments.values():
        lesson = mg.lessons[i.lesson]
        kb.row(types.InlineKeyboardButton(
            text=f"📷 {lesson.short_name}: {i.comment}",
            callback_data=f'image_{i.id}'
        ))

    # composing message
    data = mg.get_homework_dict()
    out = get_homework_text(data)

    # sending
    await call.message.edit_text(out, reply_markup=kb.as_markup())
    await call.answer()


@dp.callback_query(F.data == 'hweditor')
async def inline_editor(call: types.CallbackQuery):
    '''
    Homework editor
    '''
    # preparing
    check = mg.check(call.from_user, True)
    if check:
        await call.answer(f"❌ {check}")
        return

    log(f'{call.from_user.full_name} ({call.from_user.id}) opened homework editor')

    # creating keyboard
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text='⬅ Назад', callback_data='homework'))
    index = 3
    for i in mg.lessons.values():
        if not i.homework: continue

        button = types.InlineKeyboardButton(text=i.short_name, callback_data=f'hweditor_{i.id}')
        if index >= 3:
            kb.row(button)
            index = 0
        else:
            kb.add(button)
            index += 1

    # sending
    out = f'<b>📕 Выберите урок для изменения домашнего задания</b>'
    await call.message.edit_text(out, reply_markup=kb.as_markup())
    await call.answer()
    

@dp.callback_query(F.data.startswith('hweditor_'))
async def inline_editor_lesson(call: types.CallbackQuery):
    '''
    Action chooser in homework editor
    '''
    # preparing
    check = mg.check(call.from_user, True)
    if check:
        await call.answer(f"❌ {check}")
        return

    lesson = mg.lessons[call.data.removeprefix('hweditor_')]
    log(f'{call.from_user.full_name} ({call.from_user.id}) opened {lesson.id} in hwe')
    hw = mg.get_homework(lesson.id)

    # composing message
    out = f'<b>📕 {lesson.name}:</b>\n\n'

    if not hw:
        out += '<i>Ничего не записано</i>'

    for i in hw:
        out += utils.hw_to_string(i, user=mg.get_user(i.written_by).name)+'\n'
    
    # creating keyboard
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text='⬅ Назад', callback_data=f'hweditor'))
    kb.row(types.InlineKeyboardButton(text='➕ Добавить', callback_data=f'hwadd_{lesson.id}'))
    kb.add(types.InlineKeyboardButton(text='🗑 Удалить', callback_data=f'hwdel_{lesson.id}'))

    # images
    for i in mg.attachments.values():
        if i.lesson != lesson.id: continue
        kb.row(types.InlineKeyboardButton(
            text=f"📷 {i.comment}",
            callback_data=f'image_{i.id}'
        ))

    # sending
    await call.message.edit_text(out, reply_markup=kb.as_markup())
    await call.answer()
    

@dp.callback_query(F.data.startswith('hwadd_'))
async def inline_add_hw(call: types.CallbackQuery):
    '''
    Add homework modal
    '''
    # preparing
    check = mg.check(call.from_user)
    if check:
        await call.answer(f"❌ {check}", True)
        return

    lesson = mg.lessons[call.data.removeprefix('hwadd_')]
    log(f'{call.from_user.full_name} ({call.from_user.id}) adding homework to {lesson.id}')

    # checking availability
    if not lesson.homework:
        await call.answer('❌ Возможность записывать ДЗ на этот урок отключена', True)
        return

    mg.set_state(call.from_user.id, f'hwadd_{lesson.id}')

    # composing message
    out = f'📝 Введите домашнее задание, которое нужно записать на урок <b>{lesson.name}</b>\n\n'\
        f'<i>Вы можете прикрепить <u>максимум одно</u> изображение.</i>'
    
    # creating keyboard
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text='⬅ Назад', callback_data=f'hweditor_{lesson.id}'))

    # sending
    await call.message.edit_text(out, reply_markup=kb.as_markup())
    await call.answer()
    

@dp.callback_query(F.data.startswith('hwdel_'))
async def inline_del_hw(call: types.CallbackQuery):
    '''
    Delete homework chooser modal
    '''
    # preparing
    check = mg.check(call.from_user)
    if check:
        await call.answer(f"❌ {check}", True)
        return

    # checking availability
    lesson = mg.lessons[call.data.removeprefix('hwdel_')]
    if not mg.get_homework(lesson.id):
        await call.answer('❌ Ничего не записано', True)
        return

    log(f'{call.from_user.full_name} ({call.from_user.id}) deleting homework from {lesson.id}')

    # composing message
    out = f'📝 Выберите домашнее задание, которое нужно удалить с урока <b>{lesson.name}</b>\n\n'\
        '<i>Прикрепленные к ДЗ изображения также будут удалены.</i>'
    
    # creating keyboard
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text='⬅ Назад', callback_data=f'hweditor_{lesson.id}'))
    kb.add(types.InlineKeyboardButton(text='🗑 Удалить всё', callback_data=f'hwerase_{lesson.id}'))
    
    for i in mg.get_homework(lesson.id):
        photo_icon = '🖼 ' if i.attachment != None else ''
        kb.row(types.InlineKeyboardButton(text=f'{photo_icon}{i.text}', callback_data=f'hwrem_{i.id}'))

    # sending
    await call.message.edit_text(out, reply_markup=kb.as_markup())
    await call.answer()
    

@dp.callback_query(F.data.startswith('hwrem_'))
async def inline_rem_hw_entry(call: types.CallbackQuery):
    '''
    Delete homework entry callback
    '''
    # preparing
    check = mg.check(call.from_user)
    if check:
        await call.answer(f"❌ {check}", True)
        return

    # checking availability
    id = call.data.removeprefix('hwrem_')
    if id not in mg.homework:
        await call.answer('❌ Выбранное ДЗ не найдено', True)
        return

    hw = mg.homework[id]
    lesson = mg.lessons[hw.lesson]
    log(f'{call.from_user.full_name} ({call.from_user.id}) deleting homework entry {hw.id} from {hw.lesson}')

    mg.delete_homework(hw.id)

    # creating keyboard
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text='⬅ Назад', callback_data=f'hwdel_{hw.lesson}'))

    # sending
    out = f'🗑 Домашнее задание <b>{hw.text}</b> успешно удалено с урока <b>{lesson.name}</b>!'
    await call.message.edit_text(out, reply_markup=kb.as_markup())
    await call.answer()
    

@dp.callback_query(F.data.startswith('hwerase_'))
async def inline_erase_hw_entry(call: types.CallbackQuery):
    '''
    Erase all homework entries for one lesson callback
    '''
    # preparing
    check = mg.check(call.from_user)
    if check:
        await call.answer(f"❌ {check}", True)
        return

    # checking availability
    lesson = mg.lessons[call.data.removeprefix('hwerase_')]
    hw = mg.get_homework(lesson.id)
    log(f'{call.from_user.full_name} ({call.from_user.id}) deleting all homework from {lesson.id}')

    # composing message
    out = f'🗑 Всё ДЗ было успешно удалено с урока <b>{lesson.name}</b>!\n'
    out += f'<code>_ _ _ _ _ _ _ _ _ _ _ _ _ _ _</code>\n'
    out += f'<code>¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯</code>\n'
    out += 'Список удалённого ДЗ:\n\n'
    for i in hw:
        out += utils.hw_to_string(i, False, mg.get_user(i.written_by).name)+'\n'
        mg.delete_homework(i.id)

    # creating keyboard
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text='⬅ Назад', callback_data=f'hweditor_{lesson.id}'))
    
    # sending
    await call.message.edit_text(out, reply_markup=kb.as_markup())
    await call.answer()



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
    log(f'{call.from_user.full_name} ({call.from_user.id}) requested subject info for {subject}')

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

    # homework
    if data.homework:
        out += '📖 Домашнее задание:\n'
        hw = mg.get_homework(data.id)
        
        if not hw:
            out += '<i>Ничего не записано</i>\n'

        for i in hw:
            out += utils.hw_to_string(i, user=mg.get_user(i.written_by).name)+'\n'

    # sending
    await call.message.answer(out)
    await call.answer()

    

@dp.callback_query(F.data.startswith('image_'))
async def inline_attachment(call: types.CallbackQuery):
    '''
    Attachment view callback
    '''
    # preparing
    id = call.data.removeprefix('image_')
    check = mg.check(call.from_user)
    if check:
        await call.answer(f"❌ {check}")
        return

    log(f'{call.from_user.full_name} ({call.from_user.id}) requested image with ID {id}')

    # checking for the image
    if id not in mg.attachments:
        await call.answer('❌ Изображение не найдено', True)
        return
    image = mg.attachments[id]

    # sending
    filename = add_overlay(image)
    file = types.FSInputFile(filename)

    lesson = mg.lessons[image.lesson]
    out = f'🖼 Прикреплённое изображение к ДЗ по уроку <b>{lesson.name}</b>:\n\n'
    out += image.comment

    # keyboard
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text='❌ Отмена', callback_data='delete'))

    await call.message.answer_photo(file, out, )
    await call.answer()

    os.remove(filename)


@dp.callback_query(F.data == 'noop')
async def noop_callback(call: types.CallbackQuery):
    '''
    Does literally nothing
    '''
    await call.answer()


@dp.callback_query(F.data == 'delete')
async def delete_callback(call: types.CallbackQuery):
    '''
    Deletes a message
    '''
    await call.message.delete()
    await call.answer()


@dp.callback_query(F.data == 'reset_state')
async def reset_state_callback(call: types.CallbackQuery):
    '''
    Reset user state
    '''
    if mg.get_state(call.from_user.id) == None:
        await call.answer('❌ Текущих действий нет.', True)
    else:
        mg.reset_state(call.from_user.id)
        await call.answer('💥 Действие успешно отменено!', True)





# ---------------------------
# states
# ---------------------------


@dp.message()
async def state_handler(msg: types.Message):
    # preparing
    if msg.text != None and msg.text.startswith('/'): return # no commands
    if not msg.photo and msg.text == None: return

    state = mg.get_state(msg.from_user.id)
    if state == None: state = ''
    mg.reset_state(msg.from_user.id)


    # homework writing
    if state.startswith('hwadd_'):
        # check
        check = mg.check(msg.from_user, True)
        if check:
            await msg.reply(f"❌ {check}")
            return
        lesson = mg.lessons[state.removeprefix('hwadd_')]
        
        # checking for availability
        if not lesson.homework:
            await msg.reply("<b>❌ Операция отменена</b>\n\nВозможность записывать"\
                            " ДЗ на этот урок отключена.")
            return
        
        # checking for caption
        if msg.photo and msg.caption == None:
            await msg.reply("<b>❌ Операция отменена</b>\n\nНеобходимо написать"\
                            " текст сообщения вдобавок к изображению. Попробуйте ещё раз.")
            mg.set_state(msg.from_user.id, state)
            return
        
        # adding hw
        text = msg.text if not msg.photo else msg.caption
        attachment = None

        # attachment
        if msg.photo != None:
            loading_msg = await msg.reply('🖼 Загрузка изображения...')
            attachment = await download_image(
                msg.photo[-1].file_id, lesson, text, msg.from_user
            )

            if attachment == None:
                out = '<b>❌ Операция отменена</b>\n\nНе удалось сохранить изображение. Попробуйте ещё раз.'
                await loading_msg.edit_text(out)
                mg.set_state(msg.from_user.id, state)
                return
            
            await loading_msg.delete()

        # finishing up
        mg.add_homework(lesson.id, text, attachment, msg.from_user.id)
        log(f'{msg.from_user.full_name} ({msg.from_user.id}) added homework for {lesson.id}: {text}')

        # keyboard
        kb = InlineKeyboardBuilder()
        kb.add(types.InlineKeyboardButton(text='⬅ Назад', callback_data=f'hweditor_{lesson.id}'))
        kb.add(types.InlineKeyboardButton(text='✏ Записать ещё', callback_data=f'hwadd_{lesson.id}'))

        out = f'📚 Вы успешно записали ДЗ <b>{text}</b> на урок <b>{lesson.name}</b>'
        await msg.reply(out, reply_markup=kb.as_markup())


    # handle editing
    elif state == 'edit_handle':
        # check
        check = mg.check(msg.from_user, True)
        if check:
            await msg.reply(f"❌ {check}")
            return
        
        # checking if user already has this handle
        handle = msg.text.upper()
        user = mg.get_user(msg.from_user.id)
        if handle == user.company_handle:
            await msg.reply(f'<b>❌ Операция отменена</b>\n\n'\
                f'У вас уже установлен этот тэг. Попробуйте ещё раз.')
            mg.set_state(msg.from_user.id, state)
            return
        
        # checking balance
        if not user.handle_change_free and user.balance < config.HANDLE_CHANGE_COST:
            await msg.reply(f'<b>❌ Вам необходимо {config.HANDLE_CHANGE_COST}{config.CURRENCY}'\
                f'для изменения тэга!</b>\n\nВаш баланс: <b>{user.balance}{config.CURRENCY}</b>')
            return
        
        # checking if handle's good
        if not utils.check_handle(handle):
            await msg.reply(f'<b>❌ Операция отменена</b>\n\n'\
                f'Данный тэг не соответствует требованиям. Попробуйте ещё раз.')
            mg.set_state(msg.from_user.id, state)
            return
        
        # checking availability
        if not mg.handle_available(handle):
            await msg.reply(f'<b>❌ Операция отменена</b>\n\n'\
                f'Данный тэг уже занят. Попробуйте ещё раз.')
            mg.set_state(msg.from_user.id, state)
            return
        
        # changing handle
        try:
            mg.change_handle(user.id, handle)
        except Exception as e:
            log(str(e), level=ERROR)
            await msg.reply(f'<b>❌ Операция отменена</b>\n\n'\
                f'Не удалось изменить тэг.')
            return
        
        log(f'{msg.from_user.full_name} ({msg.from_user.id}) changed company handle to {handle}')

        # keyboard
        kb = InlineKeyboardBuilder()
        kb.add(types.InlineKeyboardButton(text='⬅ Назад', callback_data=f'company'))

        out = f'🏷 Вы успешно изменили свой тэг на <code>{handle}</code>!'
        await msg.reply(out, reply_markup=kb.as_markup())


    # name editing
    elif state == 'edit_name':
        # check
        check = mg.check(msg.from_user, True)
        if check:
            await msg.reply(f"❌ {check}")
            return
        
        # checking if user already has this name
        name = utils.check_text(msg.text)
        user = mg.get_user(msg.from_user.id)
        if name == user.company_name:
            await msg.reply(f'<b>❌ Операция отменена</b>\n\n'\
                f'У вас уже такое имя. Попробуйте ещё раз.')
            mg.set_state(msg.from_user.id, state)
            return
        
        # checking if name's good
        if len(name) > config.COMP_NAME_MAX_LENGTH:
            await msg.reply(f'<b>❌ Операция отменена</b>\n\n'\
                f'Данное имя слишком длинное. Попробуйте ещё раз.')
            mg.set_state(msg.from_user.id, state)
            return
        
        # changing name
        try:
            mg.change_comp_name(user.id, name)
        except Exception as e:
            log(str(e), level=ERROR)
            await msg.reply(f'<b>❌ Операция отменена</b>\n\n'\
                f'Не удалось изменить имя компании.')
            return
        
        log(f'{msg.from_user.full_name} ({msg.from_user.id}) changed company name to {name}')

        # keyboard
        kb = InlineKeyboardBuilder()
        kb.add(types.InlineKeyboardButton(text='⬅ Назад', callback_data=f'company'))

        out = f'🏷 Вы успешно изменили имя компании на <b>{name}</b>!'
        await msg.reply(out, reply_markup=kb.as_markup())


    # finding user
    elif state == 'find_user':
        # check
        log(f'{msg.from_user.full_name} ({msg.from_user.id}) searching for user {msg.text}')
        check = mg.check(msg.from_user, True)
        if check:
            await msg.reply(f"❌ {check}")
            return
        
        # finding user
        users: List[api.User] = mg.find_user(msg.text)

        if users == []:
            await msg.reply('❌ Пользователей не найдено. Попробуйте ещё раз.')
            mg.set_state(msg.from_user.id, state)
            return

        # getting user profile
        if len(users) == 1:
            user = users[0]
            out = get_profile_text(user)
            await msg.reply(out)
            return
        
        # returning a list of profiles
        else:
            out = f'🔍 Найдено <b>{len(users)}</b> совпадений\n\n'\
                '<i>Нажмите на нужное для просмотра профиля</i>'
            kb = InlineKeyboardBuilder()

            for user in users:
                kb.row(types.InlineKeyboardButton(
                    text=f'[{user.company_handle}] {user.company_name}',
                    callback_data=f'profile_{user.id}'
                ))

            await msg.reply(out, reply_markup=kb.as_markup())



# starting bot

log('Started polling...')
asyncio.run(dp.start_polling(bot))