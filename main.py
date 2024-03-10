
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

from PIL import Image, ImageDraw, ImageFont

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
        out += f'<code>{symbol}</code> '+\
            f'{i.start_time.hour}:{i.start_time.minute:0>2}-'\
            f'{i.end_time.hour}:{i.end_time.minute:0>2}  •  '\
            f'<b>{mg.lessons[i.name].name}</b> '\
            f'<i>({", ".join(l.room for l in mg.lessons[i.name].teachers)})</i>\n'
        # todo homework here!!

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
                written_at = datetime.datetime.fromtimestamp(x.written_at)
                photo_icon = '🖼' if x.attachment != None else ''
                out += f'•  {photo_icon} {x.text} <i>({utils.shorten_date(written_at)})</i>\n'
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
    # author
    # todo put a user here
    string = f'От {utils.shorten_string(str(attachment.written_by), 25)}'\
        f' в {utils.shorten_date(written_at)}'
    draw.text((10, image.size[1]-30), string, (255,255,255), font, 'ld')

    # watermark
    draw.text(
        (image.size[0]-10, image.size[1]-10),
        config.IMAGE_WATERMARK_TEXT, (255,255,255),
        font, 'rd'
    )
    # lesson name
    draw.text(
        (image.size[0]-10, image.size[1]-30),
        lesson.name, (255,255,255),
        bold_font, 'rd'
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
    written_at = datetime.datetime.now()
    mg.add_attachment(id, filepath, lesson.id, comment, written_at.timestamp(), written_by.id)

    return id

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

    out += f'<code>_ _ _ _ _ _ _ _ _ _ _ _ _ _ _</code>\n'
    out += f'<code>¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯ ¯</code>\n'
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
# callbacks
# ---------------------------

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
    index = 0
    for i in mg.lessons.values():
        if index >= 3:
            f = kb.row
            index = 0
        else:
            f = kb.add
            index += 1

        f(types.InlineKeyboardButton(text=i.short_name, callback_data=f'hweditor_{i.id}'))

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
        written_at = datetime.datetime.fromtimestamp(i.written_at)
        photo_icon = '🖼' if i.attachment != None else ''
        out += f'•  {photo_icon} {i.text} <i>({utils.shorten_date(written_at)})</i>\n'
    
    # creating keyboard
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text='⬅ Назад', callback_data=f'hweditor'))
    kb.row(types.InlineKeyboardButton(text='➕ Добавить', callback_data=f'hwadd_{lesson.id}'))
    kb.add(types.InlineKeyboardButton(text='🗑 Удалить', callback_data=f'hwdel_{lesson.id}'))
    kb.add(types.InlineKeyboardButton(text='✏ Изменить', callback_data=f'hwedit_{lesson.id}'))

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

    # todo: homework here !!

    # sending
    await call.message.answer(out)
    await call.answer()

    

@dp.callback_query(F.data.startswith('image_'))
async def inline_attachment(call: types.CallbackQuery):
    '''
    Attachment view callback
    '''
    # preparing
    check = mg.check(call.from_user)
    if check:
        await call.answer(f"❌ {check}")
        return

    image = mg.attachments[call.data.removeprefix('image_')]
    log(f'{call.from_user.full_name} ({call.from_user.id}) requested image with ID {image.id}')

    # sending
    filename = add_overlay(image)
    file = types.FSInputFile(filename)

    lesson = mg.lessons[image.lesson]
    out = f'🖼 Прикреплённое изображение к ДЗ по уроку <b>{lesson.name}</b>:\n\n'
    out += image.comment

    await call.message.answer_photo(file, out)
    await call.answer()

    os.remove(filename)


@dp.callback_query(F.data == 'noop')
async def noop_callback(call: types.CallbackQuery):
    '''
    Does literally nothing
    '''
    await call.answer()





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
        
        # checking for caption
        if msg.photo and msg.caption == None:
            await msg.reply("<b>❌ Операция отменена</b>\n\nНеобходимо написать"\
                            " текст сообщения вдобавок к изображению. Попробуйте ещё раз.")
            return
        
        # adding hw
        lesson = mg.lessons[state.removeprefix('hwadd_')]
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

# starting bot

log('Started polling...')
asyncio.run(dp.start_polling(bot))