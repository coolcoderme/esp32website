# profanity.py -- naive auto-flagging for the moderation queue.
# This only FLAGS messages; you approve/delete them manually in /admin.html.

# Keep the list lower-case. Substring match is intentional (catches
# "asshole" via "ass" etc.) which is a bit aggressive, so the admin
# always gets the final say.
BADWORDS = [
    "fuck", "shit", "bitch", "asshole", "bastard", "dick",
    "piss", "crap", "damn", "slut", "whore", "cunt", "prick",
    "douche", "wank", "bollocks", "nigger", "nigga" "faggot", "retard",
]


def check(text):
    if not text:
        return False, []
    low = text.lower()
    hits = [w for w in BADWORDS if w in low]
    return (len(hits) > 0), hits
