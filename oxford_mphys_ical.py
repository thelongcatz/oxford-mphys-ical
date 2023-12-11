#!/usr/bin/env python

# Oxford Physics Timetable iCalendar Generator

import requests
import icalendar
import datetime
import pytz
import bs4
import uuid
import getpass

class timetable():
    """
    A timetable object that holds ALL relevant information that goes into the final iCalendar file.
    Since the timetable hosted on the department website does not include any information on the term
    dates, we have to deduce the actual dates by adding the nth day of the mth week to the date of the
    first Monday of week 0.
    The class initialisation would gobble up every single unique entry in the timetable page so
    tailoring to one's courses should be done afterwards by invoking timetable.calendar.subcomponents.remove().
    ---
    INPUT:
    > term (str): Academic term to query for, i.e. "Michaelmas", "Hilary" or "Trinity"
    > year (int): The academic year to query for, e.g. for academic year 2023-2024, 2023 would do.
    > cohort_year (int): Which cohort to query for, e.g. 3 for 3rd years
    > start_date (datetime.datetime): The date of the first Monday of week 0
    ---
    """
    def __init__(self, term, year, cohort_year, start_date):
        self.term = term
        self.year = year
        self.cohort_year = cohort_year
        self.start_date = start_date
        self.host = 'https://www3.physics.ox.ac.uk/lectures2' # URL of the timetable query page
        self.session = self.session_setup()
        # Translate the English description of each weekday into the corresponding offset from Monday
        self.weekday_lookup = {
            'Monday': 0,
            'Tuesday': 1,
            'Wednesday': 2,
            'Thursday': 3,
            'Friday': 4
        }
        # Initialise iCalendar object and add a few attributes to comply with RFC5545
        self.calendar = icalendar.Calendar()
        self.calendar.add('prodid', f'-//Oxford Year {cohort_year} MPhys Timetable {term} {year}//EN')
        self.calendar.add('version', '2.0')
        # Create iCalendar events associated with each entry
        self.links = self.link_grabber()
        for entry in self.links:
            self.create_events(entry['course'], entry['url'], self.start_date)

    def session_setup(self):
        """
        Setup a session object for keep-alive connections and authentication if
        accessed from outside of the University network.
        """
        session = requests.Session()
        auth_test = session.get(self.host)
        if auth_test.status_code == 401:
            print('Authentication required! Please enter your Physics department credentials (NOT SSO).')
            username = input('Username: ')
            password = getpass.getpass()
            session.auth = (username, password)
        return session

    def link_grabber(self):
        """
        Obtain every unique URL of the available entries, which is to be scrapped than the timetable page.
        Why not scrap the timetable page, you ask? The afternoon segment complicates the extraction logic
        so it's simpler to extract the timetable from each lecture page as per the KISS principle.
        """
        url = f'{self.host}/timetable.aspx'
        params = {'term': self.term, 'year': self.year, 'course': f'{self.cohort_year}physics'}
        page = self.session.get(url, params=params)
        if not page.ok:
            raise RuntimeError(f'Error in getting timetable page! Status code: {page.status_code}')
        soup = bs4.BeautifulSoup(page.content, 'html.parser')
        table = soup.find('table')
        links = []
        for hyperlink in set(table.find_all('a')):
            links.append({'course': hyperlink.get_text(strip=True), 'url': f'{self.host}/{hyperlink["href"]}'})
        return links

    def create_events(self, lecture, url, start_date):
        """
        Create iCalendar events based on the information in a provided course page, i.e. the page you
        find yourself in upon clicking on one timetable entry.
        ---
        INPUT:
        > lecture (str): The course name
        > url (str): The URL to the course information on the Physics department website
        > start_date (datetime.datetime): Datetime object representing the Monday of week 0
        """
        page = self.session.get(url)
        if not page.ok:
            raise RuntimeError(f'Error in getting lecture information! Status code: {page.status_code}')
        soup = bs4.BeautifulSoup(page.content, 'html.parser')
        events = []
        # Skipping the first row since it just contains column titles
        for row in soup.find('table').find_all('tr')[1:]:
            cells = row.find_all('td')
            # As of 2023 the layout of the table is:
            # <Weekday> <Week> <Term> <Time slot> <Location>
            # strip=True gets rid of leading/trailing unwanted whitespace in the texts
            day, week, term, time_range, location = (cells[i].get_text(strip=True) for i in range(5))
            # Check if the term matches – practicals span across different terms!
            if term != self.term:
                continue
            # The hack here is due to the time string being contaminated by \r, \n, and \t's.
            # So we first split to remove the whitespaces and group the time into two, before
            # removing the extra hyphen to make the string valid.
            time_start, time_end = time_range.split()
            time_start = time_start.replace('-', '').split('.')
            time_end = time_end.split('.')
            # Construct datetime object for the event
            day_delta = start_date + datetime.timedelta(days=self.weekday_lookup[day], weeks=int(week))
            time_delta_start = datetime.timedelta(hours=int(time_start[0]), minutes=int(time_start[1]))
            time_delta_end = datetime.timedelta(hours=int(time_end[0]), minutes=int(time_end[1]))
            events.append({'name': lecture, 'start_time': day_delta + time_delta_start, \
                            'end_time': day_delta + time_delta_end, 'location': location})

        # Construct from the list above, this step is required to achieve the automated collating of
        # adjacent time slots
        start_time_first = None # Marker to check if the current loop is part of a collation, if not
                                # then store the value of the first starting time of the chain (if
                                # identical, adjacent events are found)
        for index, entry in enumerate(events):
            name = entry['name']
            start_time = entry['start_time']
            end_time = entry['end_time']
            location = entry['location']
            # Begin collation if there are identical events along the temporal chain
            # This code checks if the next entry is identical and connects to the current entry,
            # then merge the events into one by discarding the intermediate time slots
            if index+1 < len(events):
                next_event = events[index+1]
                name_next = next_event['name']
                start_time_next = next_event['start_time']
                location_next = next_event['location']
                if start_time_next == end_time and \
                    name_next == name and \
                    location_next == location:
                    if start_time_first is None: # i.e. the beginning of the chain
                        start_time_first = start_time
                    continue

            # Now we finally construct an iCalendar event
            if start_time_first is not None:
                start_time = start_time_first
            ical_event = icalendar.Event()
            ical_event.add('summary', name)
            ical_event.add('dtstart', start_time)
            ical_event.add('dtend', end_time)
            ical_event.add('dtstamp', datetime.datetime.now(tz=pytz.utc)) # RFC5545 compliance, must be UTC
            ical_event.add('location', location)
            ical_event['uid'] = uuid.uuid4() # UUID version 4 (random) for uniqueness
            ical_event['URL'] = url
            self.calendar.add_component(ical_event) # Add the event into the calendar object
            start_time_first = None # Reset the marker before the next loop

def get_monday_wk0_date(year, term):
    """
    Get the date of the Monday of week 0 from the Oxford Term Dates hosted by Wolfson College.
    The iCalendar hosted on the website assumes that each entry begins at the Sunday before,
    so for a week 0 Monday on the 2nd, the entry "0th week, xxx Term" shall begin on the 1st.
    ---
    INPUT:
    > year (int): The requested ACADEMIC YEAR so no need to +1 for Hilary/Trinity term
    > term (str): The requested academic term, i.e. "Michaelmas", "Hilary" or "Trinity"
    """
    if term in ('Hilary', 'Trinity'):
        year += 1 # Hilary/Trinity term occurs in the next calendar year
    elif term != 'Michaelmas':
        raise ValueError('Invalid term!') # It has to be invalid if the input is none of the 3
    wolfson_ical_req = requests.get('https://www.wolfson.ox.ac.uk/sites/default/files/inline-files/oxdate.ics')
    if wolfson_ical_req.ok:
        wolfson_ical = icalendar.Calendar.from_ical(wolfson_ical_req.content)
    for event in wolfson_ical.walk('VEVENT'):
        # Filter for 0th week entries before filtering for the requested year
        if event['summary'].startswith(f'0th Week, {term} Term'):
            if event['dtstart'].dt.year == year:
                # The entry begins on Sunday so increment the date by a day
                monday = event['dtstart'].dt + datetime.timedelta(days=1)
                return datetime.datetime(monday.year, monday.month, monday.day, tzinfo=pytz.timezone('Europe/London'))

if __name__ == '__main__':
    # Silly little functions for custom prompts, may be revamped in the future but it works!
    def choose_prompt(prompt, choice):
        """
        Print prompt before asking the user to choose by entering a valid index.
        If invalid, the function will loop until a valid one is given.
        ---
        INPUT:
        > prompt (str): Stuff to be displayed before asking for choices
        > choice (iterable): An iterable of possible choices
        """
        print(prompt)
        response = -1
        while response < 0 or response >= len(choice):
            for index, entry in enumerate(choice):
                print(f'{index}) {entry}')
            response = input('Enter the index of your choice: ')
            try:
                response = int(response)
            except:
                response = -1
                continue
        return choice[response]

    def number_prompt(prompt, limit_min, limit_max):
        """
        Prompt the user to enter an integer within a given range.
        The function will loop until a valid integer is given.
        ---
        INPUT:
        > prompt (str): Stuff to be displayed before asking for a number
        > limit_min (int): Minimum integer to be accepted
        > limit_max (int): Maximum integer to be accepted
        """
        print(prompt)
        response = -1
        while response < limit_min or response > limit_max:
            response = input(f'Enter the number in range [{limit_min}, {limit_max}]: ')
            try:
                response = int(response)
            except:
                response = -1
                continue
        return response

    def select_prompt(prompt, choice):
        """
        Prompts the user to select stuff from a list, this is like what you have
        in video games where you are choosing which ingredients to make a meal from.
        ---
        INPUT:
        > prompt (str): Stuff to be displayed before choosing from the list
        > choice (list): The list from which entries are selected
        """
        print(prompt)
        response = -1
        # copy() is necessary for creating another copy of the list, else a
        # view is generated and we lose an entry every time we remove one!
        output = choice.copy()
        while True:
            for index, entry in enumerate(choice):
                text = f'{index}) {entry} (selected)' if entry in output else f'{index}) {entry}'
                print(text)
            response = input('Enter the index of your choice [F to quit]: ')
            if response.upper() == 'F':
                break
            try:
                response = choice[int(response)]
            except IndexError:
                # Catch if an invalid index is supplied
                response = -1
                continue
            if response in output:
                output.remove(response)
                print(f'{response} removed from list.')
            else:
                output.insert(choice.index(response), response)
                print(f'{response} added to list.')
        return output

    term = choose_prompt('Which term of the academic year should I look at?', ('Michaelmas', 'Hilary', 'Trinity'))
    cohort_year = number_prompt('Which year group should I look at?', 1, 4)
    year = int(input('What academic year is it? e.g. 2023 for 2023–2024: '))
    start_date = get_monday_wk0_date(year, term)

    timetable = timetable(term, year, cohort_year, start_date)
    courses_all = [entry['course'] for entry in timetable.links]
    courses_selected = select_prompt('Select the courses to be placed in the calendar:', courses_all)
    courses_to_discard = set(courses_all) - set(courses_selected)
    for course in courses_to_discard:
        for event in timetable.calendar.subcomponents.copy():
            if event['summary'] == course:
                timetable.calendar.subcomponents.remove(event)

    filename = f'OxfPhysTimetable_Year{cohort_year}_{term}{year}.ics'
    with open(filename, 'wb') as f:
        f.write(timetable.calendar.to_ical())
    print(f'Calendar saved as {filename}. Exiting...')
