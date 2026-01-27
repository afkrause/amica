"""
This module provides functions to use as answers for Q&A for simple nonstatic information like date, time, weekday, month, year and season.

Each function can return the information in either German or English, based on the 'language' parameter.
Functions are linked to their respective tags in the qa files via the qa_functions dictionary.
"""

import time


def get_time(language = "de") -> str:
    """
    Get the current time as a formatted string.

    Returns:
        str: The current time formatted as "It is HH:MM o'clock." or "Es ist HH:MM Uhr."
    """

    if language == "de":
        return time.strftime("Es ist %H:%M Uhr.")
    else:
        return time.strftime("It is %H:%M o'clock.")

def get_date(language = "de") -> str:
    """
    Get the current date as a formatted string.

    Returns:
        str: The current date formatted as "Today is the DD of Month." or "Heute ist der DD. Month."
    """

    date = time.strftime("%d")
    if language == "de":
        months = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
        month = months[int(time.strftime("%m")) - 1]
        return f"Heute ist der {date}. {month}."
    else:
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        month = months[int(time.strftime("%m")) - 1]
        return f"Today is the {date} of {month}."

def get_weekday(language = "de") -> str:
    """
    Get the current weekday as a formatted string.

    Returns:
        str: The current weekday formatted as "Today is Weekday." or "Heute ist Wochentag."
    """

    if language == "de":
        week = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        weekday = week[int(time.strftime("%w"))-1]
        return f"Heute ist {weekday}."
    else:
        week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday = week[int(time.strftime("%w"))-1]
        return f"Today is {weekday}."

def get_month(language = "de") -> str:
    """
    Get the current month as a formatted string.

    Returns:
        str: The current month formatted as "It is Month." or "Es ist Monat."
    """

    if language == "de":
        months = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
        month = months[int(time.strftime("%m")) - 1]
        return f"Es ist {month}."
    else:
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        month = months[int(time.strftime("%m")) - 1]
        return f"It is {month}."

def get_season(language = "de") -> str:
    """
    Get the current season as a formatted string.

    Returns:
        str: The current season formatted as "It is Season." or "Es ist Jahreszeit."
    """

    month = int(time.strftime("%m"))
    season = (month + 1) % 12 // 3
    if language == "de":
        seasons = ["Winter", "Frühling", "Sommer", "Herbst"]
        return f"Es ist {seasons[season]}."
    else:
        seasons = ["Winter", "Spring", "Summer", "Autumn"]
        return f"It is {seasons[season]}."

def get_year(language = "de") -> str:
    """
    Get the current year as a formatted string.

    Returns:
        str: The current year formatted as "The year is YYYY." or "Wir haben das Jahr YYYY."
    """

    year = time.strftime("%Y")
    if language == "de":
        return f"Wir haben das Jahr {year}."
    else:
        return f"The year is {year}."

# link the functions to their tags in the qa files
qa_functions = {
    "@date": get_date,
    "@time": get_time,
    "@weekday": get_weekday,
    "@month": get_month,
    "@year": get_year,
}
