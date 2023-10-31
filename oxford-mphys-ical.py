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
    def __init__(self, term, year, cohort_year, start_date):
        self.start_date = start_date
        self.term = term
        self.year = year
        self.cohort_year = cohort_year
        self.host = 'https://www3.physics.ox.ac.uk/lectures'
        self.weekday_lookup = {
        'Monday': 0,
        'Tuesday': 1,
        'Wednesday': 2,
        'Thursday': 3,
        'Friday': 4
        }
        self.links = self.link_grabber()
        self.calendar = icalendar.Calendar()
        self.calendar.add('prodid', '-//Oxford Year {} Physics Timetable {} {}//EN'.format(cohort_year, term, year))
        self.calendar.add('version', '2.0')
        for entry in self.links:
            self.create_events(entry['lecture'], entry['url'], self.start_date)

    # Obtain every unique URL of the lectures available
    # Why not scrap the timetable page, you ask? The afternoon segment complicates the extraction logic
    # so it's simpler to extract the timetable from each lecture page as per the KISS principle
    def link_grabber(self):
        url = '{}/timetable.aspx'.format(self.host)
        params = {'term': self.term, 'year': self.year, 'course': '{}physics'.format(self.cohort_year)}
        page = s.get(url, params=params)
        assert page.ok, 'HTTP error in fetching timetable!'
        soup = BeautifulSoup(page.content, 'html.parser')
        table = soup.find('table')
        links = []
        for hyperlink in set(table.find_all('a')):
            links.append({'lecture': hyperlink.get_text(strip=True), 'url': '{}/{}'.format(self.host, hyperlink['href'])})
        return links

    # Create iCal events based on the information in the lecture page
    # start_date is the Monday in Week 0
    def create_events(self, lecture, url, start_date):
        page = s.get(url)
        assert page.ok, 'HTTP error in fetching lecture information!'
        soup = BeautifulSoup(page.content, 'html.parser')
        table = soup.find('table')
        raw_events = []
        for row in table.find_all('tr')[1:]:
            cells = row.find_all('td')
            # Check if the term matches - practicals span across different terms!
            if cells[2].get_text(strip=True) != self.term:
                continue
            day = cells[0].get_text(strip=True)
            week = int(cells[1].get_text(strip=True))
            time_range = cells[3].get_text(strip=True)
            location = cells[4].get_text(strip=True)
            time_start, time_end = time_range.split()
            time_start = time_start.replace('-', '')
            # Construct datetime object for the event
            day_offset = datetime.timedelta(days=self.weekday_lookup[day], weeks=week)
            day = start_date + day_offset
            event_time = []
            for i in (time_start, time_end):
                time_string = datetime.datetime.strptime(i, '%H.%M')
                time_delta = datetime.timedelta(hours=time_string.hour, minutes=time_string.minute)
                event_time.append(day + time_delta)
            raw_events.append({'name': lecture, 'start_time': event_time[0], 'end_time': event_time[1], 'location': location})

        # Construct event
        start_time_first = None
        for index, entry in enumerate(raw_events):
            name = entry['name']
            start_time = entry['start_time']
            end_time = entry['end_time']
            location = entry['location']
            # Continue if there are identical events along the temporal chain
            # This code checks if the next entry is identical, then
            # merge the events into one by discarding intermediate times
            if index+1 < len(raw_events):
                next_event = raw_events[index+1]
                name_next = next_event['name']
                start_time_next = next_event['start_time']
                location_next = next_event['location']
                if start_time_next == end_time and name_next == name and location_next == location:
                    if not start_time_first:
                        start_time_first = start_time
                    continue
            if start_time_first:
                start_time = start_time_first
            event = icalendar.Event()
            event.add('summary', name)
            event.add('dtstart', start_time)
            event.add('dtend', end_time)
            event.add('dtstamp', datetime.datetime.now(tz=pytz.utc))
            event.add('location', location)
            event['uid'] = uuid4()
            event['URL'] = url
            start_time_first = None
            # Add event to calendar
            self.calendar.add_component(event)

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
