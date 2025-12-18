# Semester Planner / Timetable Visualizer

This app will create a timetable based on given subjects and courses where you can select which class to take and export into an image, which you can use upon subject choosing in neptun.

## Requirements
- Python 3.9+ (uses only the standard library)

## CSV format
Each row:
```
<Subject_name>,<subject_code>,<Credits>,<Course_code_1>,<Course_time_1>,<Course_code_2>,<Course_time_2>,...
```
- Time format: `DAY:HH:MM-HH:MM`
- Day codes: `H` (Mon), `K` (Tue), `SZE` (Wed), `CS` (Thu), `P` (Fri)

Example (trimmed):
```
Example Subject,SUBJ123,5,E1,H:10:15-12:00,L1,CS:14:15-16:00
```
A fuller sample is in `courses.csv`.

## Project layout note
The scripts import `timetable.main` and `timetable.models`, so they expect to live in a package named `timetable`. You can either:
- Place these files inside a `timetable/` package (with an `__init__.py`) and run the commands below, **or**
- Adjust the imports to local modules (e.g., change `from timetable.models import ...` to `from models import ...`) if you keep the flat layout.

The commands below assume you use the `timetable` package layout.

## Quick start
1) Ensure the CSV is ready (see `courses.csv`).
2) Generate the interactive HTML:
```bash
python -m timetable.visualize --csv courses.csv --out timetable.html
```
3) Open the generated `timetable.html` in your browser. Toggle subjects, click blocks to select/deselect classes, then use **Export PNG** to save the chosen schedule.

## Minimal text view
To just load and print the timetable to stdout:
```bash
python -m timetable.main
```

## Notes
- The time range of the grid auto-expands to the earliest start and latest end time in the CSV.
- Overlapping classes are allowed; selection is up to you.
- Use UTF-8 CSV files; the loader opens files with `utf-8-sig`.
