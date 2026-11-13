"""Book lessons between a tutor and a student.

A lesson lasts 15 to 40 minutes, in steps of 5, and gets its own Meetly room.
"""

from dataclasses import dataclass
from datetime import datetime

from lessons.meetly import room_request

SHORTEST_MINUTES = 15
# Set to the room length on Meetly's Basic plan (see lessons/meetly.py).
LONGEST_MINUTES = 40
STEP_MINUTES = 5


class BookingError(ValueError):
    """A booking the service will not accept."""


@dataclass(frozen=True)
class Lesson:
    tutor: str
    student: str
    subject: str
    start: datetime
    minutes: int


def book(tutor, student, subject, start, minutes):
    """Return the booked lesson and the Meetly room request for it."""
    if not SHORTEST_MINUTES <= minutes <= LONGEST_MINUTES or minutes % STEP_MINUTES:
        raise BookingError("A lesson must last 15 to 40 minutes, in steps of 5.")
    lesson = Lesson(tutor, student, subject, start, minutes)
    return lesson, room_request(lesson)
