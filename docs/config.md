# YWT Configurations


## [`config.py`](../config.py)

Change basic settings for the bot, like log file output and path to database file.

All the settings in `config.py` should be documented in the file and overall self-explanatory, so I don't think I need to explain them here. Look for yourself.


## [`lessons.json`](../lessons.json)

This file, however, I need to explain here, since jsons ain't got no comments.

It contains all the data about the lessons, the schedule and the subjects in the bot.

You can look at the [example file](../lessons.json) in the repository to see how things are supposed to look.


### Lesson schedules

You need to specify the schedule for each day you have your lessons in the following format:

```json
{
    // base file
    // ...
    "thursday": { // lowercase weekday name of the day with your lessons
        "lessons": [ // list of all lesson IDs - REQUIRED
            "foo",
            "bar"
        ],
        "start_time": [12,0] // the time when the lessons start - OPTIONAL.
                             // the first number is the hour, the second is the minute
    },
    "saturday": { // lowercase weekday name of the day with your lessons
        "lessons": [ // list of all lessons - REQUIRED
            "bar",
            "foo"
        ],
        "schedule": [ // schedule data for the specific day - OPTIONAL.
                      // default schedule will be used if this is not provided
                      // uses the same format as `default_schedule`
            {"break": false, "length": 30},
            {"break": true,  "length": 10},
            {"break": false, "length": 30}
        ]
    },
    // ...
    // base file
}
```

You can put any number of weekdays you wish - they are completely optional, though if there are no weekdays with lessons in them, the bot will raise an error.

They all must contain a field called `lessons` with all lesson IDs in the day. If the day does not contain this field, it will use an empty list as the lesson list.

If you need to overwrite the default schedule, you can insert a field named `schedule`. It is optional and, if not included, will fall back to the default schedule. It uses the same format as the `default_schedule` field in the base file, which will be explained down below.

If you need to overwrite the time at which the lessons start, you can insert a field named `start_time`. It is also optional and, if not included, will fall back to the default start time. It uses the same format as the `start_time` field in the base file - `[hour_int, minute_int]` - so, for example, the `"start_time": [8,0]`'s lessons will start at 8:00 AM. It uses 24-hour time btw.


### Default values

The file must include the `default_schedule` field, which contains the data of the length and start times of lessons and breaks. Each element in the `default_schedule` list must contain a boolean `break` field, which signifies whether the current event is a break or not, and the integer `length` field, which contains the length of the event in minutes.

They also must include the `default_start_time` field, which contains the default time when lessons start in format `[hour_int, minute_int]` as already explained above.

For example:

```json
{
    // base file
    // ...
    "default_schedule": {
        {"break": false, "length": 30},
        {"break": true,  "length": 10},
        {"break": false, "length": 40}
    },
    "default_start_time": [8,0]
    // ...
    // base file
}
```

In the example above, the first lesson will start at 8:00 AM and will last 30 minutes. Then, there will be a break, starting at 8:30 AM and lasting 10 minutes. After that, there will be another lesson at 8:40 AM and lasting 40 minutes, so ending at 9:20 AM.

> Note: I don't know what will happen if you put a break first in the schedule. It's not like anything should happen, but please don't.


### Lessons

The file must contain the field named `lessons` with lesson data. Each dict in this field must contain a name of the lesson, a shortened name (recommended approx. 5 or 6 characters, but the length is up to you really), whether homework can be written for this lesson, and list of teacher names and their room numbers or places of the lesson.

For example:

```json
{
    // base file
    // ...
    "lessons": {
        "pe": { // lesson ID (put THIS in lesson schedules)
            "name": "Physical Education", // lesson name
            "short_name": "PE", // short lesson name
            "homework": false, // whether the homework can be written for this lesson
            "teachers": [ // list of teachers - putting multiple can be useful if
                          // you are dividing into different groups and working in
                          // different places with different teachers
                {
                    "name": "O. L. Chuchuyav", // teacher name
                    "room": "Street Court" // a place where the lesson is going to be
                },
                {
                    "name": "M. N. Vifiuk", // teacher name
                    "room": "Inside Court" // a place where the lesson is going to be
                }
            ]
        },
        "chemistry": { // lesson ID
            "name": "Chemistry", // lesson name
            "short_name": "Chem", // short lesson name
            "homework": true, // whether the homework can be written for this lesson
            "teachers": [ // list of teachers
                {
                    "name": "C. F. Atstivak", // teacher name
                    "room": "28" // a place where the lesson is going to be
                }
            ]
        }
    }
    // ...
    // base file
}
```

The way it is supposed to work and the description of the different fields is explained above in the codeblock.
