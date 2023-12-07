#!/usr/bin/env python3

# Oxford Physics Timetable iCalendar Generator

import requests, icalendar, datetime, pytz
from bs4 import BeautifulSoup
from uuid import uuid4

s = requests.Session()
s.headers = {
'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:68.0) Gecko/20100101 Firefox/68.0',
'Accept': '*/*',
'Accept-Language': 'en-US,en;q=0.5',
'Connection': 'keep-alive'
}

class timetable():
    """
    A timetable object that holds ALL relevant information that goes into the final iCalendar file.
    Since the timetable hosted on the department website does not include any information on the term
    dates, we have to deduce the actual dates by adding the nth day of the mth week to the date of the
    first Monday of week 0.
    The class initialisation would gobble up every single unique entry in the timetable page so
    tailoring to one's courses should be done afterwards by invoking
    timetable.calendar.subcomponents.remove().
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
        self.host = 'https://www3.physics.ox.ac.uk/lectures' # URL of the timetable query page
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
            self.create_events(entry['lecture'], entry['url'], self.start_date)

    def link_grabber(self):
        """
        Obtain every unique URL of the available entries, which is to be scrapped than the timetable page.
        Why not scrap the timetable page, you ask? The afternoon segment complicates the extraction logic
        so it's simpler to extract the timetable from each lecture page as per the KISS principle.
        """
        url = f'{self.host}/timetable.aspx'
        params = {'term': self.term, 'year': self.year, 'course': f'{self.cohort_year}physics'}
        page = s.get(url, params=params)
        if not page.ok:
            raise Exception('HTTP error in fetching timetable!')
        soup = BeautifulSoup(page.content, 'html.parser')
        table = soup.find('table')
        links = []
        for hyperlink in set(table.find_all('a')):
            links.append({'lecture': hyperlink.get_text(strip=True), 'url': f'{self.host}/{hyperlink["href"]}'})
        return links

    def create_events(self, lecture, url, start_date):
        """
        Create iCalendar events based on the information in a provided course page, i.e. the page you
        find yourself in upon clicking on one timetable entry.
        """
        page = s.get(url)
        if not page.ok:
            raise Exception('HTTP error in fetching lecture information!')
        soup = BeautifulSoup(page.content, 'html.parser')
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
            if index+1 < len(raw_events):
                next_event = raw_events[index+1]
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
            ical_event['uid'] = uuid4() # UUID version 4 (random) for uniqueness
            ical_event['URL'] = url
            self.calendar.add_component(ical_event) # Add the event into the calendar object
            start_time_first = None # Reset the marker before the next loop

if __name__ == '__main__':
    def choose_prompt(prompt, choice):
        print(prompt)
        response = -1
        while response < 0 or response >= len(choice):
            for i, j in enumerate(choice):
                print('{}) {}'.format(i, j))
            response = input('Enter the index of your choice: ')
            try:
                response = int(response)
            except:
                response = -1
                continue
        return choice[response]

    def number_prompt(prompt, limit_min, limit_max):
        print(prompt)
        response = -1
        while response < limit_min or response > limit_max:
            response = input('Enter the number in range [{}, {}]: '.format(limit_min, limit_max))
            try:
                response = int(response)
            except:
                response = -1
                continue
        return response

    def select_prompt(prompt, choice):
        print(prompt)
        response = -1
        output = choice.copy()
        while True:
            for i, j in enumerate(choice):
                text = '{}) {} (selected)'.format(i, j) if j in output else '{}) {}'.format(i, j)
                print(text)
            response = input('Enter the index of your choice [F to quit]: ')
            if response in ('f', 'F'):
                break
            try:
                response = choice[int(response)]
            except:
                response = -1
                continue
            if response in output:
                output.remove(response)
                print('{} removed from list.'.format(response))
            else:
                output.insert(choice.index(response), response)
                print('{} added to list.'.format(response))
        return output

    term = choose_prompt('Which term of the academic year should I look at?', ('Michaelmas', 'Hilary', 'Trinity'))
    print()
    cohort_year = number_prompt('Which year group should I look at?', 1, 4)
    print()
    year = int(input('What year is it? '))
    print()
    start_month = number_prompt('What is the month where Week 0 lies?', 1, 12)
    print()
    start_day = number_prompt('What is the day where Monday of Week 0 lies?', 0, 31)
    start_date = datetime.datetime(year, start_month, start_day, tzinfo=pytz.timezone('Europe/London'))

    filename = 'OxfPhysTimetable_Year{}_{}{}.ics'.format(cohort_year, term, year)

    timetable = timetable(term, year, cohort_year, start_date)
    courses_all = [i['lecture'] for i in timetable.links]
    courses_selected = select_prompt('Select the courses to be placed in the calendar:', courses_all)
    courses_to_discard = set(courses_all) - set(courses_selected)
    for course in courses_to_discard:
        for event in timetable.calendar.subcomponents.copy():
            if event['summary'] == course:
                timetable.calendar.subcomponents.remove(event)

    with open(filename, 'wb') as f:
        f.write(timetable.calendar.to_ical())
    print('Calendar saved as {}. Exiting...'.format(filename))
