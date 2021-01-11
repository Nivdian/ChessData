# TODO: Handle spreadsheet creation a bit more smoothly(?)
# TODO: Lichess support
# TODO: Trendline
# TODO: Win/loss ratio stuff.

import sys
import re
from datetime import datetime
import datetime as dt
import requests
import matplotlib.pyplot as plt
import os
import time as sleeptime
import shutil
import calendar
import math
from tqdm import tqdm
import matplotlib.ticker as ticker
from json.decoder import JSONDecodeError
import matplotlib.dates as mdates

timeformat = '%H:%M:%S'  # Needed for datetime.
interval = 5  # Datapoints for x-values.
plt.tight_layout()
print('Welcome! This program is used to calculate playtime for chess.com users in specified time spans.')


def truncate(number, decimals=0):
    """
    Returns a value truncated to a specific number of decimal places.
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer.")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more.")
    elif decimals == 0:
        return math.trunc(number)

    factor = 10.0 ** decimals
    return math.trunc(number * factor) / factor


def start_end_input(text):  # Start_end_input does basic error handling.
    while True:
        error_text = '\nYear must be an integer between 1900 and ' + str(dt.date.today().year) + \
                     ' and month must be an integer between 1 and 12.'
        error_text2 = '\nDate must be expressed in YYYY-MM format.'
        print(text)
        response = input()
        try:
            response_split = response.split('-')
            year = int(response_split[0])
            month = int(response_split[1])

            if 1900 > year or year > dt.date.today().year:
                print(error_text)

            elif month < 0 or month > 12:
                print(error_text)
            else:
                return year, month
        except ValueError:
            print(error_text)
        except IndexError:
            print(error_text2)


def create_date_tuples(start_year, start_month, end_year, end_month):
    month_number = (end_year - start_year) * 12 + (end_month - start_month + 2)  # +2 bc subtraction.
    date_tuple_list = []
    current_month = start_month
    current_year = start_year

    for i in range(0, (month_number - 1)):  # -1 to avoid off-by-one error.
        if current_month > 12:  # If this is bigger, then year needs to be increased.
            current_year += 1
            current_month -= 12

        date_tuple = (current_year, current_month)  # Creates tuple of year and month
        date_tuple_list.append(date_tuple)  # Adds tuple to list.
        current_month += 1  # Increases the month by one.
    return date_tuple_list


def get_json(year, month):
    if month < 10:  # Chess.com api has format 09, 08 etc...
        url = 'https://api.chess.com/pub/player/' + usrname + '/games/' + str(year) + '/0' + str(month)
    else:
        url = 'https://api.chess.com/pub/player/' + usrname + '/games/' + str(year) + '/' + str(month)

    response = requests.get(url)  # Fetch url content. (JSON)

    try:
        return response.json()  # Turn data from response into readable json.
    except JSONDecodeError:
        print('\nRan into unexpected decoding error. Possibly due to non ASCII-characters in username.')
        quit_program('Press Enter to quit...')
        sys.exit()  # Needs to be here to not raise IDE concern.


def add_time(time_to_add, adder):
    a_datetime = dt.datetime.combine(dt.date.today(), time_to_add)
    new_datetime = a_datetime + adder
    return new_datetime.time()


def extract_duration(pgn):
    start_time = extract_from_pgn(pgn, 'StartTime')
    end_time = extract_from_pgn(pgn, 'EndTime')
    result = datetime.strptime(end_time, timeformat) - datetime.strptime(start_time, timeformat)  # Time diff
    return result


def extract_from_pgn(pgn, variable_name):
    variable_text = ""
    pgn_list = pgn.splitlines()  # Splits pgn into list of rows.

    for row in pgn_list:
        variable_index = row.find(variable_name)  # finds the index of the variable name from PGN
        if variable_index == 1:  # If it's other value, it's either Date, endDate or not there.
            variable_text = row  # Variabletext is the whole
            break
    if variable_text == "":
        raise ValueError('PGN file did not contain the variable')  # TODO: Is this ok?

    variable = re.search('"(.*)"', variable_text).group(1)  # Fancy way to extract string between ""
    return variable


def readable_date(m):
    if m < 10:
        str_m = '0' + str(m)
    else:
        str_m = str(m)
    return str_m


def quit_program(message):
    input(message)
    sys.exit()


startYear, startMonth = start_end_input('Which date will be the starting date? (YYYY-MM)')
endYear, endMonth = start_end_input('Which date will be the ending date? (YYYY-MM)')

print('What is your Chess.com username?')
usrname = str(input()).capitalize()


foldername = 'Data for user ' + usrname + ''
try:
    os.mkdir(foldername)  # TODO: Exception for when file is open.
except FileExistsError:  # If folder exists, wipe data and rewrite it.
    print('A folder named "Data for user ' + usrname + '" already exists, permission to delete folder content? (Y/N)')
    answ = input()
    while True:
        if answ.lower() == 'n' or answ.lower() == 'no':
            print('This program needs permission to delete the folder. Please make a backup and try again.')
            quit_program('Press Enter to exit...')
        elif answ.lower() == 'y' or answ.lower() == 'yes':
            sleeptime.sleep(0.1)  # time to catch up
            try:
                shutil.rmtree(foldername)  # deletes entire folder.
            except PermissionError:
                input('Content of the folder "Data for user ' + usrname + '" is open in another program. Please close '
                      'that program and press Enter to continue...')
                continue
            sleeptime.sleep(0.1)  # time to catch up
            os.mkdir(foldername)
            break
        else:
            print('\nPlease answer either "Y" or "N".')
            print('A folder named Data for user "' + usrname +
                  '" already exists, permission to delete folder content? (Y/N)')
            answ = input()

rowsToBeWritten = []  # Variable for writing to .txt
accumulatedTime = 0
totalMonths = 0
accumulatedGameNum = 0

dateTupleList = create_date_tuples(startYear, startMonth, endYear, endMonth)

accumulatedTimeList = []
accumulatedDayList = []

for dateTuple in dateTupleList:  # Iterates 1 month at a time.

    year = dateTuple[0]
    month = dateTuple[1]
    strMonth = readable_date(month)

    dayList = []
    timeList = []
    dayDateList = []
    dayTimeList = []
    totalTime = dt.time(0, 0, 0)
    dayTime = dt.time(0, 0, 0)
    dayDate = dt.date(1920, 1, 1)  # TODO: Empty date?
    previousDayDate = dt.date(1920, 1, 1)  # TODO: Empty date?
    numberOfGamesForMonth = 0

    data = get_json(year, month)

    firstIteration = True
    try:
        if len(data['games']) == 0:  # If list of games is empty.
            print('No games found for ' + str(year) + '-' + str(strMonth) + '...')
            continue
    except KeyError:
        quit_program('\nNo data found for user "' + usrname +
                     '" in the specified time span. Check spelling and try again. Press enter to quit...')

    print('\nProcessing ' + str(year) + '-' + str(strMonth) + '...')
    sleeptime.sleep(0.1)  # To give progress bar a chance to catch up.
    for game in data['games']:  # Header is named games. Game is a list with variables for individually iterated games.
        # tqdm is used for progress bar in some fancy way.

        if game['time_class'] == 'daily':  # If it's daily, it's not relevant.
            continue  # If it's daily, it's irrelevant for time played.

        dayDate_text = extract_from_pgn(game['pgn'], 'Date')  # Function that finds date from pgn file.
        dayDate_text_split = dayDate_text.split('.')
        dayDate = dt.date(int(dayDate_text_split[0]), int(dayDate_text_split[1]), int(dayDate_text_split[2]))

        duration = extract_duration(game['pgn'])  # Finds duration for game.
        totalTime = add_time(totalTime, duration)  # Adds duration to total time

        previousDayTime = dayTime  # Daytime will be redifined
        numberOfGamesForMonth += 1  # Number of games played this month.

        if dayDate != previousDayDate and not firstIteration:  # Fist Iteration has problems.
            dayTimeList.append(previousDayTime)  # If it's a new day, the old day is complete.
            dayDateList.append(previousDayDate)  # Same goes here.
            previousDayDate = dayDate  # DayDate will be redefined.
            dayTime = dt.time(0, 0, 0)  # If new day, the dayTime should be 0.

        if dayDate == previousDayDate:  # if it's the same day, the daytime should increase
            dayTime = add_time(dayTime, duration)  # Adds duration to the time of the day

        if firstIteration:
            previousDayDate = dayDate  # To prevent previousDayDate = 1920, 1, 1
            firstIteration = False

    if len(dayTimeList) < 1 or len(dayDateList) < 1:
        continue

    hourPerDayList = []
    monthTime = 0.0
    for time in dayTimeList:  # get a list with hours instead of whole time.
        hours = time.hour
        minutes = time.minute
        minutefloat = minutes / 60
        hours = float(hours + minutefloat)
        hourPerDayList.append(hours)
        monthTime += hours

    sleeptime.sleep(0.1)  # Time for console print output to catch up.
    print('Creating graph for ' + str(year) + '-' + str(strMonth) + '...')

    plt.style.use('seaborn-dark')
    sleeptime.sleep(0.5)
    plt.bar(dayDateList, hourPerDayList)

    # Calculate a trendline  # TODO: Create trendline
    # z = numpy.polyfit(dayDateList, hourPerDayList, 1)
    # p = numpy.poly1d(z)
    # plt.plot(dayDateList, p(dayDateList), "r--")
    sleeptime.sleep(0.5)
    plt.xlabel('Day of month')
    plt.ylabel('Hours')
    plt.title('Hours in Chess.com games per day for user "' + usrname + '" in ' +
              str(calendar.month_name[month]).capitalize() + ' ' + str(year))

    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%d"))
    plt.gca().xaxis.set_major_locator(ticker.MaxNLocator(5))  # In some way this sets up an interval.

    # plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=interval))  # In some way this sets up an interval.

    plt.grid()

    plt.savefig((foldername + '/' 'Time Played for ' + usrname + ' ' + str(year) + '-' + str(strMonth) + '.png'),
                dpi=199)
    plt.clf()  # Clears entire statistic.

    accumulatedGameNum += numberOfGamesForMonth

    monthText = 'Playtime in ' + str(calendar.month_name[month]).capitalize() + ' was ' + \
                str(round(monthTime, 1)) + ' hours, or ' + str(numberOfGamesForMonth) + ' games.'
    rowsToBeWritten.append(monthText)
    accumulatedTime += monthTime
    totalMonths += 1

    for item in dayDateList:
        accumulatedDayList.append(item)
    for item in hourPerDayList:
        accumulatedTimeList.append(item)


plt.style.use('seaborn-dark')
plt.bar(accumulatedDayList, accumulatedTimeList)

plt.xlabel('Date')
plt.ylabel('Hours')
plt.title('Hours in Chess.com games per day for user "' + usrname + '"')

plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
plt.gca().xaxis.set_major_locator(ticker.MaxNLocator(5))  # In some way this sets up an interval.

plt.grid()

plt.savefig((foldername + '/' 'Total Time Played for ' + usrname + '.png'), dpi=199)
plt.clf()  # Clears entire statistic.

accumulatedTime = round(accumulatedTime, 1)

txtFilePath = foldername + '\\' + usrname + '.txt'
txtFile = open(txtFilePath, 'w+')
txtFile.write('Data from Chess.com for user "' + usrname + '"')
txtFile.write('\n\n')

for row in rowsToBeWritten:
    txtFile.write(row)
    txtFile.write('\n')


txtFile.write('\n')
txtFile.write('Average playtime per month was ' + str(round(accumulatedTime / totalMonths, 1)) + ' hours, or '
              + str(round(accumulatedGameNum / totalMonths, 1)) + ' games.')
txtFile.write('\n')
txtFile.write('Average playtime per day was ' + str(round(accumulatedTime / (totalMonths * 30), 1)) + ' hours, or '
              + str(round(accumulatedGameNum / (totalMonths*30), 1)) + ' games.')
txtFile.write('\n')
txtFile.write('Total playtime was ' + str(accumulatedTime) + ' hours, or ' + str(accumulatedGameNum) + ' games.')

averageDuration = accumulatedTime/accumulatedGameNum * 60
txtFile.write('\n')
txtFile.write('Average game duration was ' + str(round(averageDuration, 1)) + ' minutes.')

txtFile.close()

quit_program('\nDone! Press Enter to quit...')
