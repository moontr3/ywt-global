from typing import *

import os
import datetime
import json
from log import *
import utils
import time
from aiogram.types import User as AiogramUser
import random


# homework entry

class HomeworkEntry:
    def __init__(self,
        id:str, lesson:str, text:str,
        attachment:str,
        written_at:float, written_by:int
    ):
        '''
        A homework entry.
        '''
        self.id: str = id # homework ID
        self.lesson: str = lesson # lesson ID
        self.text: str = text # homework text
        self.attachment: str = attachment # attachment ID
        self.written_at: float = written_at # timestamp when written
        self.written_by: int = written_by # user ID who wrote it

    def to_dict(self) -> dict:
        '''
        Converts the data to a dictionary to store in the database.
        '''
        return {
            "lesson": self.lesson,
            "text": self.text,
            "attachment": self.attachment,
            "written_at": self.written_at,
            "written_by": self.written_by
        }
    

# attachment

class Attachment:
    def __init__(
        self, id:str, filename:str, lesson:str,
        comment:str, written_at:float, written_by:int
    ):
        '''
        Represents an attachment to a homework assignment.
        '''
        self.id: str = id # attachment ID
        self.filename: str = filename # attachment file
        self.lesson: str = lesson # lesson
        self.comment: str = comment # attachment comment
        self.written_at: float = written_at # timestamp when written
        self.written_by: int = written_by # user ID who wrote it

    def to_dict(self) -> dict:
        '''
        Converts the data to a dictionary to store in the database.
        '''
        return {
            "filename": self.filename,
            "lesson": self.lesson,
            "comment": self.comment,
            "written_at": self.written_at,
            "written_by": self.written_by
        }
    
    def from_dict(id:str, data:dict):
        return Attachment(
            id,
            data['filename'],
            data['lesson'],
            data['comment'],
            data['written_at'],
            data['written_by']
        )
    

# lesson
    
class Teacher:
    def __init__(self, data:dict):
        '''
        Represents a teacher.
        '''
        self.name: str = data['name'] # teacher name
        self.room: str = data['room'] # room name
    
class Lesson:
    def __init__(self, id:str, data:dict):
        '''
        Represents a lesson in the schedule.
        '''
        assert len(data['teachers']) > 0, "Lessons must have at least one teacher/room"
        self.id: str = id # lesson ID
        self.name: str = data['name'] # lesson name
        self.short_name: str = data['short_name'] # shortened lesson name
        self.homework: bool = data['homework'] # is homework available
        self.teachers: List[Teacher] = [Teacher(i) for i in data['teachers']] # list of teachers


# day
    
class Event:
    def __init__(self, start_timestamp:int, data:dict):
        '''
        Represents a lesson or a break in the schedule.
        '''
        self.is_break: bool = data['break'] # is this event a break 
        self.length: int = data['length'] # length of the event
        self.length_seconds: int = data['length']*60 # length of event in seconds
        self.name: str = data['name'] # lesson name (None if no lesson for this event)
        
        self.start_timestamp: int = start_timestamp # start timestamp
        self.end_timestamp: int = start_timestamp+self.length_seconds # end timestamp

        self.start_time = datetime.datetime.fromtimestamp(self.start_timestamp) # start datetime
        self.end_time = datetime.datetime.fromtimestamp(self.end_timestamp) # end datetime


class Day:
    def __init__(self, begin_time:datetime.datetime, lessons:List[str], schedule:List[dict]):
        '''
        Represents a single day in the schedule.
        '''
        assert len([i for i in schedule if not i['break']]) >= len(lessons),\
            "Too few lesson events in schedule data"

        self.lessons: List[str] = lessons # list of lessons
        self.schedule: List[dict] = schedule # schedule data
        self.begin_time: datetime.datetime = begin_time # time when lessons begin
        self.begin_timestamp: int = begin_time.timestamp() # timestamp when lessons begin 
        self.weekday = begin_time.weekday()

        self.events: List[Event] = []
        event_time = int(self.begin_timestamp)
        lesson_index = 0

        for i in self.schedule:
            if len(lessons)-1 == lesson_index:
                self.lesson_end_timestamp: int = int(event_time+i['length']*60)
                self.lesson_end_time = datetime.datetime.fromtimestamp(
                    event_time+i['length']*60
                )

            if not i['break'] and lesson_index < len(lessons):
                # pasting in lesson info
                i['name'] = self.lessons[lesson_index]
                lesson_index += 1
            else:
                i['name'] = None

            self.events.append(Event(event_time, i))
            event_time += i['length']*60 # because time in schedule data is in minutes
            
        self.end_timestamp: int = event_time
        self.end_time = datetime.datetime.fromtimestamp(self.end_timestamp)


# current time data

class Time:
    def __init__(self, day:Day, weekday_index:int):
        '''
        Contains current time info, like is the school going right now,
        the time until the next event, etc.
        '''
        self.time = datetime.datetime.now()
        self.weekday: int = day.weekday

        time_td = utils.to_td(self.time)
        start_td = utils.to_td(day.begin_time)
        end_td = utils.to_td(day.end_time)
        
        self.is_school: bool = (weekday_index == self.weekday)\
            and ((start_td < time_td) and (end_td > time_td))
        self.event: Event = None # the current event of the day
        self.event_index: int = None # the index of the event in the day
        self.event_number: int = None # the number of the event like 5th break or 1st lesson
        self.time_remaining: int = None # time remaining until next event

        if self.is_school:
            breaks_thru = 0
            lessons_thru = 0
            lessons = len(day.lessons)

            for index, i in enumerate(day.events):
                cur_td = utils.to_td(i.start_time)

                if i.is_break: breaks_thru += 1
                else: lessons_thru += 1

                if cur_td+i.length_seconds > time_td:
                    self.event_index = index
                    self.event = i
                    self.event_number = breaks_thru if i.is_break else lessons_thru
                    self.time_remaining = (i.length_seconds+cur_td)-time_td
                    break

                if lessons_thru > lessons:
                    self.is_school = False
                    break
            else:
                self.is_school = False


# user data
                
class SlotToilet:
    def __init__(self, id:str, working_until:int, work_start:int):
        '''
        Represents a working toilet.
        '''
        self.id: str = id # toilet ID
        self.working_until: int = working_until # timestamp when the toilet should stop working
        self.work_start: int = work_start # timestamp of when the toilet started working

    def to_dict(self) -> dict:
        return {
            "working_until": self.working_until,
            "work_start": self.work_start
        }

                
class Slot:
    def __init__(
        self, toilet_data:dict=None,
        stamina_restored_at:int=0
    ):
        '''
        A slot in which you put your toilets to flush
        '''
        self.toilet_data: SlotToilet = SlotToilet(toilet_data) if toilet_data else None
        self.stamina_restored_at: int = stamina_restored_at

    def to_dict(self) -> dict:
        return {
            "toilet_data": self.toilet_data.to_dict() if self.toilet_data else None,
            "stamina_restored_at": self.stamina_restored_at
        }
                

class User:
    def __init__(
        self, id:int, full_name:str, handle:str,
        balance:int=config.DEFAULT_BALANCE,
        daily_until:int=0,
        max_slots:int=config.MAX_SLOTS_AMOUNT,
        slots:List[Dict]=[],
        company_name:str=None,
        company_handle:str=None,
        handle_change_free:bool=True,
        **kwargs
    ):
        '''
        A user entry in a database
        '''
        self.id: int = int(id) # telegram user id
        self.full_name: str = full_name # telegram account name and surname
        self.handle: str = handle # telegram username, can be none
        self.name: str = utils.check_text(handle if handle else full_name) # user name to display

        self.company_name: str = self.name if not company_name else company_name # the name of the company
        self.company_handle: str =\
            utils.to_handle(self.full_name) if not company_handle else company_handle # the handle of the company
        self.handle_change_free: bool = handle_change_free
        self.balance: int = balance # current user's economy balance
        self.daily_until: int = daily_until # timestamp after which the daily reward may be collected
        self.max_slots: int = max_slots # maximum amount of slots
        self.slots: List[Slot] = [Slot(**i) for i in slots]

    def to_dict(self) -> dict:
        return {
            "full_name": self.full_name,
            "handle": self.handle,
            "balance": self.balance,
            "daily_until": self.daily_until,
            "max_slots": self.max_slots,
            "slots": [i.to_dict() for i in self.slots],
            "company_name": self.company_name,
            "company_handle": self.company_handle,
            "handle_change_free": self.handle_change_free
        }
        
    def update_name(self, full_name:str, handle:str) -> bool:
        '''
        Updates the name and the handle of the user.
        '''
        changed = False

        if self.full_name != full_name:
            log(f'User {self.id} changed full name from {self.full_name} to {full_name}')
            self.full_name = full_name
            changed = True

        if self.handle != handle:
            log(f'User {self.id} changed handle from {self.handle} to {handle}')
            self.handle = handle
            changed = True

        if changed:
            self.name: str = utils.check_text(handle if handle else full_name) # user name to display

        return changed
        


# main manager

class Manager:
    def __init__(self, lessons_file:str, db_file:str):
        '''
        Manages basically the entire bot.
        '''
        self.lessons_file = lessons_file # path to file with lesson data
        self.db_file = db_file # path to database file

        self.states: Dict[int, str] = {} # list of user states

        self.reload_lessons()
        self.reload_db()


    def clone_db(self):
        '''
        Copies the database into a backup file.
        '''
        with open(self.db_file, encoding='utf8') as f:
            data = f.read()

        with open(f'{self.db_file}.bak', 'w', encoding='utf8') as f:
            f.write(data)


    def commit_db(self):
        '''
        Pushes all data to the database file.
        '''
        data = {
            "users": {
                i: self.users[i].to_dict() for i in self.users
            },
            "homework": {
                i: self.homework[i].to_dict() for i in self.homework
            },
            "attachments": {
                i: self.attachments[i].to_dict() for i in self.attachments
            },
            "blacklist": self.blacklist,
            "write_blacklist": self.write_blacklist
        }
        with open(self.db_file, 'w', encoding='utf8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


    def create_db(self):
        '''
        Creates the database if one doesn't exist or is corrupted.
        '''
        self.homework: Dict[str, HomeworkEntry] = {}
        self.attachments: Dict[str, Attachment] = {}
        self.blacklist: List[int] = []
        self.write_blacklist: List[int] = []
        self.users: Dict[int, User] = {}

        self.commit_db()


    def reload_lessons(self):
        '''
        Loads lesson data from the file.
        '''
        with open(self.lessons_file, encoding='utf8') as f:
            raw_lessons: dict = json.load(f)

        # lessons
        self.lessons: Dict[str, Lesson] = {
            i: Lesson(i, raw_lessons['lessons'][i]) for i in raw_lessons['lessons']
        }

        # schedule
        schedule = raw_lessons['default_schedule'] # default schedule
        self.start_time: List[int] = raw_lessons['default_start_time'] # 1st value is hours, 2nd is minutes

        default = {"lessons": []}
        weekdays: List[dict] = [
            raw_lessons.get('monday', default), 
            raw_lessons.get('tuesday', default),
            raw_lessons.get('wednesday', default),
            raw_lessons.get('thursday', default),
            raw_lessons.get('friday', default),
            raw_lessons.get('saturday', default),
            raw_lessons.get('sunday', default),
        ]

        self.schedule: List[Day] = [] # this is the default schedule
        for i in weekdays:
            # getting starting time
            # and yes i fucking HATE THIS SHIT IVE BEEN SITTING HERE FOR LIKE 5 HOURS MY HEAD FUCKING HURTS SO MUCH SMH
            start_time_format = i.get('start_time', self.start_time)
            start_time = datetime.datetime.now() # we don't really care about the date
                                                 # right now so we can just pass in anything
            start_time = datetime.datetime(
                start_time.year, start_time.month, start_time.day,
                start_time_format[0],  start_time_format[1], 0, 0
            )

            self.schedule.append(Day(
                start_time,
                i.get('lessons', []),
                i.get('schedule', schedule)
            ))

        self.available_days: List[int] = [
            index for index,i in enumerate(self.schedule) if len(i.lessons) > 0
        ] # list of days with lessons
        assert len(self.available_days) > 0, "No weekdays with lessons found in them"

        # substitutions
        # self.update_substitutions()


    def reload_db(self):
        '''
        Loads the database.
        '''
        # checking if database exists
        if not os.path.exists(self.db_file):
            self.create_db()
            return

        # reading the database
        try:
            with open(self.db_file, encoding='utf8') as f:
                raw_db: dict = json.load(f)
        # creating the database
        except:
            self.clone_db()
            self.create_db()
            return

        # loading data
        homework = raw_db.get('homework', {})
        self.homework: Dict[str, HomeworkEntry] =\
            {i: HomeworkEntry(id=i, **homework[i]) for i in homework}
        
        attachments = raw_db.get('attachments', {})
        self.attachments: Dict[str, Attachment] =\
            {i: Attachment(id=i, **attachments[i]) for i in attachments}
        
        self.blacklist: List[int] = raw_db.get('blacklist', [])
        self.write_blacklist: List[int] = raw_db.get('write_blacklist', [])

        users = raw_db.get('users', {})
        self.users: Dict[int, User] =\
            {int(i): User(id=i, **users[i]) for i in users}

        self.commit_db()
        

    def check(self, user:AiogramUser, write_action:bool=False) -> str:
        '''
        Checks if the user is allowed to use the bot and performs
        some manipulations with user if needed.

        Will return `str` with the error if something goes wrong,
        otherwise will return None.
        '''
        # resetting user state
        self.reset_state(user.id)

        # checking user
        if user.id not in self.users:
            self.new_user(user)

        changed = self.users[user.id].update_name(user.full_name, user.username)

        # economy slots
        while len(self.users[user.id].slots) < self.users[user.id].max_slots:
            self.users[user.id].slots.append(Slot())
            changed = True

        # commiting if needed
        if changed:
            self.commit_db()
        

        # checking permissions
        if user.id in config.ADMINS: return None # все равны но админы ровнее

        # blacklist
        if not config.USE_WHITELIST and user.id in self.blacklist:
            return 'Пользователь в черном списке'
        
        # whitelist
        if config.USE_WHITELIST and user.id not in self.blacklist:
            return 'Пользователь не в белом списке'
        
        if write_action:
            # write blacklist
            if not config.USE_WRITE_WHITELIST and user.id in self.write_blacklist:
                return 'Нет прав для записи - Пользователь в чёрном списке'
            
            # write blacklist
            if config.USE_WRITE_WHITELIST and user.id not in self.write_blacklist:
                return 'Нет прав для записи - Пользователь не в белом списке'
            

    def add_to_blacklist(self, id:int) -> bool:
        '''
        Adds user to a blacklist/whitelist.

        Returns a boolean whether adding was successful.
        '''
        if id in self.blacklist: return False
        self.blacklist.append(id)
        return True
        

    def remove_from_blacklist(self, id:int) -> bool:
        '''
        Removes user from a blacklist/whitelist.

        Returns a boolean whether removing was successful.
        '''
        if id not in self.blacklist: return False
        self.blacklist.remove(id)
        return True
    

    def write_availability(self, id:int) -> bool:
        '''
        Returns whether the user with the given ID can
        write to the DB (like writing homework etc.).
        '''
        if id in config.ADMINS: return True

        if not config.USE_WRITE_WHITELIST and id in self.write_blacklist\
            or config.USE_WRITE_WHITELIST and id not in self.write_blacklist:
                return False
        
        return True
    

    def get_state(self, id:int) -> str:
        '''
        Returns the state of the user with the given ID.

        If no state, returns None.
        '''
        return self.states.get(id, None)
    

    def set_state(self, id:int, state:str=None):
        '''
        Sets the state of the user.
        '''
        if state == None:
            self.reset_state(id)
            return
        
        self.states[id] = state


    def reset_state(self, id:int):
        '''
        Removes the state of the user.
        '''
        if id in self.states:
            self.states.pop(id)


    def new_user(self, user:AiogramUser):
        '''
        Creates a new user.
        '''
        if user.id in self.users:
            return
        
        self.users[user.id] = User(user.id, user.full_name, user.username)
        self.commit_db()


    def get_user(self, id:int) -> User:
        '''
        Returns a user if found in the database.
        Otherwise returns None.
        '''
        if id not in self.users:
            return None
        
        return self.users[id]
    

    def get_schedule(self, weekday_index:int) -> Day:
        '''
        Returns a schedule data for the day.
        '''
        assert weekday_index in self.available_days, "No such weekday available"

        # todo substitutions
        day = self.schedule[weekday_index]
        day.weekday = datetime.datetime.now().weekday()
        return day
        

    def next_available_weekday(self, start_weekday:int) -> int:
        '''
        Returns the next available weekday index (next weekday index with
        lessons at such day).
        '''
        weekday = int(start_weekday)

        while weekday not in self.available_days:
            weekday += 1
            if weekday > 6:
                weekday = 0

            assert weekday != start_weekday, 'No available days found'

        return weekday
    

    def get_summary(self) -> Day:
        '''
        Returns the schedule that is used in the /summary command
        and its weekday index.
        '''
        cur_time = datetime.datetime.now()
        weekday: int = cur_time.weekday()

        if weekday not in self.available_days:
            # just showing the next available day
            weekday = self.next_available_weekday(weekday)
            return self.get_schedule(weekday), weekday
        
        else:
            day: Day = self.get_schedule(weekday)

            if cur_time.hour > day.lesson_end_time.hour or\
            (cur_time.hour == day.lesson_end_time.hour\
            and cur_time.minute >= day.lesson_end_time.minute): 
                # if the current day is available and the school time had already passed
                weekday = self.next_available_weekday((weekday+1)%7)
                return self.get_schedule(weekday), weekday
            else:
                # if the school is still in progress
                return day, weekday
        

    def occurences(self, lesson:str) -> List[Tuple[int,int]]:
        '''
        Returns all occurences of the given lesson in the
        weekly schedule.

        Returns a list of tuples with weekday indexes and
        lesson indexes.
        '''
        out = []

        for day in self.available_days:
            for index, l in enumerate(self.schedule[day].lessons):
                if l == lesson:
                    out.append((day, index))
        
        return out
    

    def add_homework(self,
        lesson:str, text:str,
        attachment:str,
        written_by:int
    ) -> str:
        '''
        Adds a homework entry and returns its ID.
        '''
        id = utils.rand_id()
        self.homework[id] = HomeworkEntry(
            id, lesson, utils.check_text(text), attachment,
            time.time(), written_by
        )
        self.commit_db()
        return id
    

    def delete_homework(self, id:str):
        '''
        Deletes a homework entry.
        '''
        if id not in self.homework:
            return
        
        attachment = self.homework[id].attachment
        self.homework.pop(id)

        if attachment:
            self.delete_attachment(attachment)

        self.commit_db()
    

    def add_attachment(self,
        id:str, filename:str, lesson:str,
        comment:str, written_at:int,
        written_by:int
    ):
        '''
        Adds an attachment.
        '''
        self.attachments[id] = Attachment(
            id, filename, lesson, comment,
            written_at, written_by
        )
        self.commit_db()


    def delete_attachment(self, id:str):
        '''
        Deletes an attachment.
        '''
        if id not in self.attachments:
            return
        
        attachment = self.attachments[id]
        if os.path.exists(attachment.filename):
            os.remove(attachment.filename)
        self.attachments.pop(id)
        self.commit_db()
    

    def get_homework_dict(self) -> Dict[str, List[HomeworkEntry]]:
        '''
        Returns a dict with lesson **names** as keys and lists of
        homework objects as values.
        '''
        data = {}
        for i in self.lessons.items():
            hw = self.get_homework(i[0])
            if hw:
                data[i[1].name] = hw

        return data


    def get_homework(self, lesson:str) -> List[HomeworkEntry]:
        '''
        Returns all homework written for a specific lesson.
        '''
        return [i for i in self.homework.values() if i.lesson == lesson]
    
    
    def get_attachment(self, id:str) -> Attachment:
        '''
        Returns an attachment by its ID.

        Returns None if there is no such attachment.
        '''
        return self.attachments[id] if id in self.attachments else None
    

    def get_writable_lessons(self) -> Lesson:
        '''
        Returns all lessons with the ability to write homework.
        '''
        return [i for i in self.lessons.values() if i.homework]
    

    def handle_available(self, handle:str) -> bool:
        '''
        Returns whether the handle is not occupied on any user
        and can be set on anyone.
        '''
        for i in self.users.values():
            if i.company_handle == handle:
                return False
            
        return True
    

    def find_user(self, string:str) -> List[User]:
        '''
        Finds users in the database by name, handle, company
        handle or company name and returns a list of successful
        matches.
        '''
        out = []
        for user in self.users.values():
            if user.handle.lower().startswith(string.lstrip('@').lower()) or\
                user.company_handle == string.upper() or\
                user.full_name.lower().startswith(string.lower()) or\
                user.company_name.lower().startswith(string.lower()):
                    out.append(user)
            
        return out
    

    def add_balance(self, id:int, amount:int) -> int:
        '''
        Adds certain amount of money to a player's account.

        If succeeded, returns the current amount of money in
        the player's account.
        '''
        if id not in self.users:
            return
        
        user = self.users[id]
        user.balance += amount
        self.users[id] = user
        
        self.commit_db()


    def collect_daily(self, id:int) -> int:
        '''
        Collects a daily reward.

        Returns the collected amount. If can't collect daily
        reward or user not found, returns None.
        '''
        if id not in self.users:
            self.users[id]
            return
        
        if self.users[id].daily_until > time.time():
            return
        
        amount = random.randint(*config.DAILY_REWARD_RANGE)
        user = self.users[id]
        user.balance += amount
        user.daily_until = time.time()+config.DAILY_REWARD_TIMEOUT
        self.users[id] = user

        self.commit_db()
        return amount
    
    
    def change_handle(self, id:int, handle:str, charge:bool=True):
        '''
        Changes the user's company handle to the provided one.
        '''
        user = self.users[id]
        user.company_handle = handle
        # taking money
        if charge:
            if not user.handle_change_free:
                assert user.balance >= config.HANDLE_CHANGE_COST,\
                    'Insufficient funds'
                user.balance -= config.HANDLE_CHANGE_COST
            else:
                user.handle_change_free = False
    
        # updating db
        self.users[id] = user
        self.commit_db()
    
    
    def change_comp_name(self, id:int, name:str):
        '''
        Changes the user's company name to the provided one.
        '''
        user = self.users[id]
        user.company_name = name
        self.users[id] = user

        self.commit_db()
