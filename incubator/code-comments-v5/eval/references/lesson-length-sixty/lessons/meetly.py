"""Requests to Meetly, the video service that hosts every lesson."""

ROOMS_URL = "https://api.meetly.example/v2/rooms"


def room_request(lesson):
    """The JSON body for the POST to ROOMS_URL that opens one lesson's room."""
    # Meetly's Basic plan, which this account is on, closes every room 40 minutes
    # after it opens, whatever duration_minutes says.
    return {
        "title": f"{lesson.subject} with {lesson.tutor}",
        "starts_at": lesson.start.isoformat(),
        "duration_minutes": lesson.minutes,
        "waiting_room": True,
    }
