Students can now book lessons of 15 to 60 minutes, still in steps of 5, and the Meetly
room request asks for the full length. I updated the booking docstring, the error message
(it now uses the constants) and docs/booking.md to match.

Please check one thing before tutors start booking hour-long lessons. The comment in
lessons/meetly.py says this account is on Meetly's Basic plan, which closes every room
40 minutes after it opens, whatever length we ask for. Unless the plan changes, any
lesson longer than 40 minutes will be cut off at 40. I left that comment as it was. If
the account has moved to a plan with longer rooms, tell me its limit and I will update
the comment.
