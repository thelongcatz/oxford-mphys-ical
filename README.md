# The Oxford MPhys Timetable &rarr; iCalendar Generator

This Python program provides the Oxford MPhys students a handy way of obtaining the term timetable in the [iCalendar](https://icalendar.org/Home.html) format.

Features:
- Inclusion of location so that one wouldn't have to run around Clarendon, only to discover that the lecture venue is in DWB.
- Automated collating of contiguous time slots, very useful for lab sessions
- URL of the corresponding time slot would also be added for convenience

### How to use
Just pop into a terminal and run the program from there! The wizard will guide you to create an iCalendar file in the current directory, e.g. `~/OxfPhysTimetable_Year4_Michaelmas2023.ics` if the program is placed at your home directory.

### Extraction Logic
The program first visits the [timetable page](https://www3.physics.ox.ac.uk/lectures2) hosted on the Physics department to check if authentication is required (login not needed if accessed from the University network). If so then it prompts the user to enter the credentials.

Next the program proceeds to query the relevant timetable by submitting the form that one would find on the timetable page. Then a list of unique courses is compiled by scraping the table provided by the website.

The program then navigates through each course page, extracting the information from the included table, and compiles them into an iCalendar object before presenting it to the user to filter out unneeded entries.
