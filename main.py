# Input csv file:
# <Subject_name>,<subject_code>,<Credits>,<Course_code_1>,<Course_time_1>,<Course_code_2>,<Course_time_2>,...
# Time is in format "CS:10:15-12:00"
import csv
from timetable.models import Timetable, Subject, Course

def load_timetable_from_csv(file_path):
    timetable = Timetable()
    
    with open(file_path, newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row or all(not cell.strip() for cell in row):
                continue
            subject_name = row[0]
            subject_code = row[1]
            credits = int(row[2])
            subject = Subject(subject_name, subject_code, credits)
            
            for i in range(3, len(row), 2):
                if i + 1 >= len(row):
                    break
                course_code = row[i]
                course_time = row[i+1]
                if not course_code.strip() or not course_time.strip():
                    continue
                course = Course(course_code, course_time)
                subject.add_course(course)
            
            timetable.add_subject(subject)
    
    return timetable

if __name__ == "__main__":
    timetable = load_timetable_from_csv('timetable.csv')
    print(timetable)
    
    #D:/Projects/pytest/venv/Scripts/python.exe -m timetable.visualize --csv timetable/sample_timetable.csv --out timetable/sample_timetable.html