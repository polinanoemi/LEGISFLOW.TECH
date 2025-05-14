SOZD_DUMA_FLAG = 1
REGULATION_FLAG = 0

CREATE_PROJECT = "INSERT INTO projects (link, file_name, shortened_text, full_text, id, type, project_name, creation_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
CREATE_WORD = "INSERT INTO words VALUES (?)"
SELECT_WORD_BY_TEXT = 'SELECT ROWID FROM words WHERE text=?'
SEARCH_WORD = "SELECT id FROM projects WHERE ' ' || full_text || ' ' LIKE '% ' || ? || ' %'"
CREATE_CONNECTION = "INSERT INTO connections (project_id, word_id) VALUES (?, ?)"
SELECT_CONNECTIONS_BY_WORD = "SELECT project_id FROM connections WHERE word_id=?"
SEARCH_IN_NEW_PROJECT = 'SELECT ROWID FROM words WHERE instr((SELECT full_text FROM projects WHERE id=?) > 0, text)'
SELECT_FOR_LOWERING = 'SELECT id, full_text FROM projects'
UPDATE_TEXT = "UPDATE projects SET full_text=? WHERE id=?"
PROJECT_TEXT_BY_ID = "SELECT full_text FROM projects WHERE id=?"
SELECT_ALL_WORDS = "SELECT text, ROWID FROM words"
SELECT_FROM_LIST = "SELECT text FROM lists_words WHERE list_id=?"
CREATE_LIST_CONNECTION = "INSERT INTO lists_words (list_id, word_id) VALUES (?, ?)"
GET_LIST_CONNECTIONS_WORDS = "SELECT word_id FROM lists_words WHERE list_id=?"
DELETE_LIST_CONNECTION = "DELETE FROM lists_words WHERE list_id=? AND word_id=?"
UPDATE_SUBSCRIPTION = "UPDATE subscriptions SET enabled=? WHERE user_id=? AND list_id=?"
CREATE_LIST = "INSERT INTO lists (creator_id, name, public) VALUES (?, ?, 0)"
GET_LIST_ID_BY_INFO = "SELECT ROWID FROM lists WHERE creator_id=? AND name=?"
UPDATE_LIST_NAME = "UPDATE lists SET name=? WHERE ROWID=?"
SELECT_LAST_LINK = "SELECT link FROM projects WHERE id=(SELECT MIN(id) FROM projects WHERE type = ?) "
SELECT_FIRST_LINK = "SELECT link FROM projects WHERE id=(SELECT MAX(id) FROM projects WHERE type = ?) "

GET_EMAIL = 'SELECT email FROM users WHERE ROWID=?'
GET_USER_BY_EMAIL = "SELECT ROWID FROM users WHERE email=?"
GET_USER_ID = 'SELECT ROWID FROM users WHERE email=? AND password=?'
GET_USER_BY_TEMP = 'SELECT ROWID FROM users WHERE email=? AND temp_password=?'
CREATE_USER = "INSERT INTO users (email, first_email, password, name, token) VALUES (?, ?, ?, ?, ?)"
SET_TEMP_PASSWORD = "UPDATE users SET temp_password=? WHERE ROWID=?"
CHECK_FOR_TEMP = "SELECT temp_password FROM users WHERE ROWID=?"
CHANGE_PASSWORD = "UPDATE users SET password=? WHERE ROWID=?"
GET_USER_DATA = "SELECT email, name, password FROM users WHERE ROWID=?"
SET_NEW_NAME = "UPDATE users SET name=? WHERE ROWID=?"
SET_NEW_EMAIL = "UPDATE users SET email=? WHERE ROWID=?"
SET_NEW_PASSWORD = "UPDATE users SET password=? WHERE ROWID=?"
GET_NAME = "SELECT name FROM users WHERE ROWID=?"
CHECK_MAIL = "SELECT ROWID FROM users WHERE ? IN (email, first_email)"
CHECK_SUB = "SELECT list_id FROM subscriptions WHERE user_id=? AND list_id=?"
ADD_SUBSCRIPTION = "INSERT INTO subscriptions (enabled, user_id, list_id) VALUES (?, ?, ?)"
FLIP_ENABLED = 'UPDATE subscriptions SET enabled = not enabled WHERE user_id=? AND list_id=?'
GET_LIST_INFO_BY_ID = "SELECT creator_id, name, public FROM lists WHERE ROWID=?"
GET_LISTS_ALL = """SELECT l.ROWID AS list_id, l.name, wrds.text as word
FROM lists l
         LEFT JOIN lists_words lw ON l.ROWID = lw.list_id
         LEFT JOIN words wrds ON lw.word_id = wrds.ROWID
WHERE l.public = 1
ORDER BY l.ROWID, lw.word_id
"""
GET_LISTS_PUBLIC_UNSUBBED = """SELECT l.ROWID AS list_id, l.name, wrds.text as word
FROM lists l
         LEFT JOIN lists_words lw ON l.ROWID = lw.list_id
         LEFT JOIN words wrds ON lw.word_id = wrds.ROWID
         LEFT JOIN subscriptions sub ON sub.list_id = l.ROWID AND sub.user_id = ?
WHERE l.public = 1 AND sub.list_id IS NULL
ORDER BY l.ROWID, lw.word_id"""
GET_LISTS_INFO_SUBBED = """SELECT l.ROWID AS list_id, l.name, wrds.text as word, sub.enabled
FROM lists l
         LEFT JOIN lists_words lw ON l.ROWID = lw.list_id
         LEFT JOIN words wrds ON lw.word_id = wrds.ROWID
         LEFT JOIN subscriptions sub ON sub.list_id = l.ROWID AND sub.user_id = ?
WHERE sub.list_id IS NOT NULL
ORDER BY l.ROWID, lw.word_id"""

CONNECTIONS_BY_LIST_ID = '''SELECT
    c.project_id,
    w.text
FROM
    lists_words lw
        JOIN
    words w ON w.ROWID = lw.word_id
        JOIN
    connections c ON c.word_id = lw.word_id
WHERE
    lw.list_id = ?
ORDER BY
    c.project_id;'''
GET_SUBBED_IDS = 'SELECT list_id, ls.name FROM subscriptions JOIN lists ls ON ls.ROWID=list_id WHERE user_id=? AND enabled=1'
PROJECT_INFO_BY_ID = "SELECT creation_date, link, project_name, shortened_text, type FROM projects WHERE id=?"
GET_WORD_BY_ID = "SELECT text FROM words WHERE ROWID=?"
GET_PROJECT_VIEWERS = """SELECT DISTINCT s.user_id FROM connections
               left join main.lists_words lw on connections.word_id = lw.word_id
               left join main.subscriptions s on lw.list_id = s.list_id
               WHERE project_id=?"""
CREATE_NOTIFICATION = "INSERT INTO notifications (user_id, project_id) VALUES (?, ?)"
SELECT_USER_BY_TG = "SELECT ROWID FROM users WHERE tg_id=?"
GET_TG_ID = "SELECT tg_id FROM users WHERE ROWID=?"
TOKEN_CHECK = "SELECT ROWID FROM users WHERE token=?"
SET_TG_ID = 'UPDATE users SET tg_id=? WHERE ROWID=?'
GET_TOKEN = "SELECT token FROM users WHERE ROWID=?"
GET_PROJECT_TYPE = "SELECT type FROM projects WHERE id=?"


def format_id(project_id, project_type):
    if project_type == SOZD_DUMA_FLAG:
        tmp = str(project_id)
        return tmp[:-1] + '-' + tmp[-1]
    else:
        return str(project_id)


class LinksList:
    def __init__(self, cursor, list_type:int, stop_after=0):
        self.links = []
        self.last_link_found = False
        self.first_link_found = False
        self.last_seen_link = ''
        self.first_seen_link = ''
        self.length = 0
        self.__curr = 0
        self.stop_after = stop_after
        self.type = list_type
        check = cursor.execute(SELECT_LAST_LINK, (self.type,)).fetchone()
        if check:
            self.last_seen_link = check[0]
            self.first_seen_link = cursor.execute(SELECT_FIRST_LINK, (self.type,)).fetchone()[0]

    def __getitem__(self, item: int):
        return self.links[item]

    def __setitem__(self, key: int, value):
        self.links[key] = value

    def __iter__(self):
        return self

    def __next__(self):
        if self.__curr < self.length:
            self.__curr += 1
            return self.links[self.__curr-1]
        else:
            raise StopIteration()


    def append(self, link: str):
        if not self.first_link_found:
            if link == self.first_seen_link:
                self.first_link_found = True
                return
            self.links.append(link)
            self.length += 1
        else:
            if not self.last_link_found and link == self.last_seen_link:
                self.last_link_found = True
                return
            if self.last_link_found:
                self.links.append(link)
                self.length += 1
        if self.stop_after and self.length == self.stop_after:
            return 1

    def clear(self):
        self.links.clear()

    def __len__(self):
        return self.length
