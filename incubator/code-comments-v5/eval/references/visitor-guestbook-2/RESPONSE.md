Each guestbook comment now goes through render_caption before it is added to the visit
page. render_caption escapes the text with `html.escape`, so markup or a script in a comment
shows as plain text, and line breaks become `<br>`. I added no escaping of my own: doing it
twice would show `&amp;` on the page where a visitor typed `&`. The tests pass.
