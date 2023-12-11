# The Oxford MPhys Timetable &rarr; iCalendar Generator

This Python program provides the Oxford MPhys students a handy way of obtaining the term timetable in the [iCalendar](https://icalendar.org/Home.html) format.

Features:
- Inclusion of location so that one wouldn't have to run around Clarendon, only to discover that the lecture venue is in DWB.
- Automated collating of contiguous time slots, very useful for lab sessions
- URL of the corresponding time slot would also be added for convenience

### How to use
Just pop into a terminal and run the program from there! The wizard will guide you to create an iCalendar file in the current directory, e.g. `~/OxfPhysTimetable_Year4_Michaelmas2023.ics` if the program is placed at your home directory.

```
$ python oxford_mphys_ical.py
Which term of the academic year should I look at?
0) Michaelmas
1) Hilary
2) Trinity
Enter the index of your choice: 0
Which year group should I look at?
Enter the number in range [1, 4]: 4
What academic year is it? e.g. 2023 for 2023–2024: 2023
Authentication required! Please enter your Physics department credentials (NOT SSO).
Username: abcd1234
Password:
Select the courses to be placed in the calendar:
0) Astro Opt (selected)
1) BiologicalPhys Opt (selected)
2) Theory Opt (selected)
3) CMP Opt (selected)
4) Project Safety (selected)
5) Particle Opt (selected)
6) Atmos Opt (selected)
7) Lasers and Q.I.P. (selected)
Enter the index of your choice [F to quit]: 6
Atmos Opt removed from list.
0) Astro Opt (selected)
1) BiologicalPhys Opt (selected)
2) Theory Opt (selected)
3) CMP Opt (selected)
4) Project Safety (selected)
5) Particle Opt (selected)
6) Atmos Opt
7) Lasers and Q.I.P. (selected)
Enter the index of your choice [F to quit]: 6
Atmos Opt added to list.
0) Astro Opt (selected)
1) BiologicalPhys Opt (selected)
2) Theory Opt (selected)
3) CMP Opt (selected)
4) Project Safety (selected)
5) Particle Opt (selected)
6) Atmos Opt (selected)
7) Lasers and Q.I.P. (selected)
Enter the index of your choice [F to quit]: f
Calendar saved as OxfPhysTimetable_Year4_Michaelmas2023.ics. Exiting...
```

### Extraction Logic
The program first visits the [timetable page](https://www3.physics.ox.ac.uk/lectures2) hosted on the Physics department to check if authentication is required (login not needed if accessed from the University network). If so then it prompts the user to enter the credentials.

Next the program proceeds to query the relevant timetable by submitting the form that one would find on the timetable page. Then a list of unique courses is compiled by scraping the table provided by the website.

The program then navigates through each course page, extracting the information from the included table, and compiles them into an iCalendar object before presenting it to the user to filter out unneeded entries.
