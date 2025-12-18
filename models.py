class Timetable:
    def __init__(self):
        self.subjects = []

    def add_subject(self, subject):
        self.subjects.append(subject)

    def __str__(self):
        return "\n".join(str(subject) for subject in self.subjects)

DAYS_OF_WEEK = ['H', 'K', 'SZE', 'CS', 'P']

class Time:
    def __init__(self, hour, minute):
        self.hour = hour
        self.minute = minute

    @staticmethod
    def from_string(value: str):
        hour_str, minute_str = value.split(':')
        return Time(int(hour_str), int(minute_str))

    def to_minutes(self) -> int:
        return self.hour * 60 + self.minute

    def __str__(self):
        return f"{self.hour:02}:{self.minute:02}"

class ClassTime:
    def __init__(self, day, start_time, end_time):
        self.day = day  # e.g., 'CS'
        self.start_time = start_time  # Time object
        self.end_time = end_time      # Time object

    def __str__(self):
        return f"{self.day}:{self.start_time}-{self.end_time}"

    
class Course:
    def __init__(self, code, time):
        self.code = code
        self.time = time
        
    def get_time(self):
        # e.g: CS:10:15-12:00
        day_part, hours_part = self.time.split(':', 1)
        if day_part not in DAYS_OF_WEEK:
            raise ValueError(f"Invalid day '{day_part}' in course time '{self.time}'")

        start_time_str, end_time_str = hours_part.split('-')
        start_time = Time.from_string(start_time_str)
        end_time = Time.from_string(end_time_str)
        return ClassTime(day_part, start_time, end_time)        
        
    def __str__(self):
        return f"Course {self.code} at {self.time}"
    
class Subject:
    def __init__(self, name, code, credits):
        self.name = name
        self.code = code
        self.credits = credits
        self.courses = []

    def add_course(self, course):
        self.courses.append(course)

    def __str__(self):
        return f"Subject: {self.name} ({self.code}, {self.credits} credits)\n" + \
               "\n".join(str(course) for course in self.courses)
    