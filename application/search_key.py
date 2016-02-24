# Herein we find a reimplementation of the various rules applied by the legacy search routine
# and by the more modern web-based (Portal) system.
# The legal position is 'do what the existing service does', so here goes...
# We also need to get this right so that the data synchronised back into the legacy systems
# is unchanged - if we get this wrong, the Portal service will be adversely impacted.

# On registration we create a 'searchable name key' and store that (indexed) in the database
# This is similar but not identical to the key used by the legacy system. It can easily be
# converted (by Synchroniser) to *be* identical to the legacy key
from application import app
import re
import psycopg2


# Some look up tables etc.
NOISE = ['AND', 'OF', 'FOR', 'TO', '&']

COMMON_WORDS = {
    'ASS': ['ASS', 'ASSOC', 'ASSOCS', 'ASSOCIATE', 'ASSOCIATED', 'ASSOCIATES', 'ASSOCIATION', 'ASSOCIATIONS'],
    'LD': ['LD', 'PUBLIC LIMITED COMPANY', 'CWMNI CYFYNGEDIG CYHOEDDUS', 'CWMNI CYF CYHOEDDUS', 'LTD', 'LIMITED',
           'CYFYNGEDIG', 'CYF', 'CCC', 'C C C', 'PLC', 'P L C'],
    'SOC': ['SOC', 'SOCS', 'SOCY', 'SOCYS', 'SOCIETY', 'SOCIETYS', 'SOCIETIES'],
    'ST': ['ST', 'STREET', 'SAINT'],
    'CO': ['CO', 'COS', 'COY', 'COMP', 'COYS', 'COMPS', 'COMPANY', 'COMPANIES'],
    'DR': ['DR', 'DOC', 'DOCTOR'],
    'BRO': ['BRO', 'BROS', 'BROTHER', 'BROTHERS'],
    'AND': ['&', 'AND'],
    # 'BROKER': ['BROKERS'],
    # 'BUILDER': ['BUILDERS'],
    # 'COLLEGE': ['COLLEGES'],
    # 'COMMISSIONER': ['COMMISSIONERS'],
    # 'CONSTRUCTION': ['CONSTRUCTIONS'],
    # 'CONTRACTOR': ['CONTRACTORS'],
    # 'DECORATOR': ['DECORATORS'],
    # 'DEVELOPER': ['DEVELOPERS'],
    # 'DEVELOPMENT': ['DEVELOPMENTS'],
    # 'ENTERPRISE': ['ENTERPRISES'],
    # 'ESTATE': ['ESTATES'],
    # 'GARAGE': ['GARAGES'],
    # 'HOLDING': ['HOLDINGS'],
    # 'HOTEL': ['HOTELS'],
    # 'INVESTMENT': ['INVESTMENTS'],
    # 'MOTOR': ['MOTORS'],
    # 'PRODUCTION': ['PRODUCTIONS'],
    # 'SCHOOL': ['SCHOOLS'],
    # 'SON': ['SONS'],
    # 'STORE': ['STORES'],
    # 'TRUST': ['TRUSTS'],
    # 'WARDEN': ['WARDENS'],
    'CHARITY': ['CHARITIES'],
    'PROPERTY': ['PROPERTIES'],
    'INDUSTRY': ['INDUSTRIES']
}

S_WORDS = ['BROKERS', 'BUILDERS', 'COLLEGES', 'COMMISSIONERS', 'CONSTRUCTIONS', 'CONTRACTORS', 'DECORATORS',
           'DEVELOPERS', 'DEVELOPMENTS', 'ENTERPRISES', 'ESTATES', 'GARAGES', 'HOLDINGS', 'HOTELS',
           'INVESTMENTS', 'MOTORS', 'PRODUCTIONS', 'SCHOOLS', 'SONS', 'STORES', 'TRUSTS', 'WARDENS']


COMPLEX_NAME_INDICATORS = ['ARCHBISHOP', 'ARCHDEACON', 'AUTHORITY', 'BISHOP', 'BUILDING SOCIETY',
                           'BUILDING SOC', 'BUILDING SOCY', 'CATHEDRAL', 'CATHOLIC', 'CHAPEL', 'CHARITY',
                           'CHARITIES', 'CHURCH', 'COLLEGE', 'COLLEGES', 'CONGREGATIONAL', 'CO-OPERATIVE',
                           'CO OPERATIVE', 'COOPERATIVE', 'CO-OP', 'CO OP', 'COOP', 'COMMISIONER',
                           'COMMISSIONERS', 'COUNCIL', 'DEAN', 'DIOCESAN', 'FELLOWSHIP', 'FOUNDATION',
                           'GOVERNOR', 'GOVERNORS', 'HOSPITAL', 'INCORPORATED', 'INC', 'INCUMBENT',
                           'MASTER', 'MINISTER', 'MINISTRY', 'METHODIST', 'RECTOR', 'REGISTERED',
                           'ROYAL', 'SANATORIUM', 'SCHOOL', 'SCHOOLS', 'STATE', 'TRUST', 'TRUSTS', 'TRUSTEE',
                           'TRUSTEES', 'UNIVERSITY', 'VICAR', 'WARDEN', 'WARDENS']



LA_ABBREVIATIONS = {
    'SAINT': 'ST',
    'SAINTS': 'ST',
    'NORTH': 'N',
    'SOUTH': 'S',
    'WEST': 'W',
    'EAST': 'E',
    'NORTHWEST': 'NW',
    'SOUTHWEST': 'SW',
    'NORTHEAST': 'NE',
    'SOUTHEAST': 'SE',
    'SUPER': 'S',
    'SUR': 'S'
}

NON_KEY_WORDS = ['BOARD', 'GOVERNOR', 'GOVENORS', 'GUARDIAN', 'GUARDIANS', 'INCUMBENT', 'INCORPORATED',
                 'INC', 'PROPRIETOR', 'PROPRIETORS', 'REGISTERED', 'TRUSTEE', 'TRUSTEES']

LA_NON_KEY_WORDS = ['AND', '&', 'AT', 'BY', 'CITY', 'CUM', 'DE', 'DU', 'EN', 'IN', 'LA', 'LE',
                    'NEXT', 'OF', 'ON', 'OVER', 'OUT', 'SEA', 'THE', 'U', 'UNDER', 'UPON', 'WITH']


# TODO: remove this once we pass a cursor in
def connect(cursor_factory=None):
    connection = psycopg2.connect("dbname='{}' user='{}' host='{}' password='{}'".format(
        app.config['DATABASE_NAME'], app.config['DATABASE_USER'], app.config['DATABASE_HOST'],
        app.config['DATABASE_PASSWORD']))
    return connection.cursor(cursor_factory=cursor_factory)


def complete(cursor):
    cursor.connection.commit()
    cursor.close()
    cursor.connection.close()
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def remove_non_alphanumeric(name_string):
    return re.sub('[^A-Za-z0-9]', '', name_string)


def create_private_name_key(private):
    # Note that the name key for PIs will not be used by synchroniser - sync will
    # recreate it and keep the 'lost' information in the legacy hex-code thing.
    name_text = ''.join(private['forenames']) + private['surname']
    return remove_non_alphanumeric(name_text.upper())


def remove_common_words(name_array):
    # Cover the rules for 'common words', 'trailing S words' and the rule about
    # three very specific words ending in 'ies'
    for index, word in enumerate(name_array):
        for common in COMMON_WORDS:
            options = COMMON_WORDS[common]
            if word in options:
                name_array[index] = common

        if word in S_WORDS:
            name_array[index] = word[0:-1]

    return name_array


def remove_noise(name_array):
    if (len(name_array) > 0 and name_array[0] == 'THE') or \
       (len(name_array) > 0 and name_array[0] == 'MESSRS'):
        del(name_array[0])

    if len(name_array) > 0 and name_array[-1] == 'THE':
        del(name_array[-1])

    return [word for word in name_array if word not in NOISE]


def remove_non_key(name_array, words_to_remove):
    return [word for word in name_array if word not in words_to_remove]


def replace_la_abbreviations(name_array):
    for index, word in enumerate(name_array):
        if word in LA_ABBREVIATIONS:
            name_array[index] = LA_ABBREVIATIONS[word]
    return name_array


def create_limited_name_key(company):
    name_array = company.upper().split(' ')
    name_array = remove_common_words(name_array)
    name_array = remove_noise(name_array)
    name_array = remove_non_key(name_array, NON_KEY_WORDS)
    name = ' '.join(name_array)
    return remove_non_alphanumeric(name)


def fetch_name_key(cursor, name):
    cursor.execute('SELECT key FROM county_search_keys WHERE name=%(name)s', {'name': name})
    rows = cursor.fetchall()
    if len(rows) == 0:
        raise RuntimeError('No variants found for name {}'.format(name))
    if len(rows) > 1:
        raise RuntimeError('Too many variants found for name {}'.format(name))
    key = rows[0]['key']
    complete(cursor)
    return key


def create_local_authority_key(area):
    area_array = area.upper().split(' ')
    area_array = remove_non_key(area_array, LA_NON_KEY_WORDS)
    area_array = replace_la_abbreviations(area_array)
    area = ' '.join(area_array)
    area = remove_non_alphanumeric(area)
    if area == '':
        area = 'NULL KEY'
    return area


# VARNAM A where
# Not more than 4 words
# None of the words are plexnam words
# Also includes surname-only

# VARNAM B where
# not more then 4 significant (non-noise) words
# The full name (excluding non-significant words) contains one or more of:
#    plexnam word
#    common code word
#    noise or non-key
#    trailing s
# includes surname-only where the name is a special word in the group immediately above

def count_words(name_array):
    # a group of initials is one word; e.g. B O F Howard is a two word name...
    count = 0
    previous_was_1_char = False
    for name in name_array:
        if len(name) > 1:
            count += 1
            previous_was_1_char = False
        else:
            if not previous_was_1_char:
                count += 1
            previous_was_1_char = True
    return count


def contains_complex_indicators(name):
    for indicator in COMPLEX_NAME_INDICATORS:
        if re.search('(^|\s){}(\s|$)'.format(indicator), name) is not None:
            return True
    return False


def is_class_b(name):
    # This is a bit strange. In the 'other' column (legacy speak: 'VARNAM' [Various Name Types])
    # we have two sub-types, called 'A' and 'B'; they are treated differently, so we need to distinguish them
    # IMPORTANT: PLEXNAM NAMES CAN CONTAIN SPACES

    #re.search('(^|\s){}(\s|$)'.format('tri'), S))




def create_registration_key(cursor, name):
    if name['type'] == 'Private Individual':
        return create_private_name_key(name['private'])
    elif name['type'] == 'Limited Company':
        return create_limited_name_key(name['company'])
    elif name['type'] == 'County Council':
        return fetch_name_key(cursor, name['local']['area'])
    elif name['type'] in ['Parish Council', 'Rural Council', 'Other Council']:
        return create_local_authority_key(name['local']['area'])
    elif name['type'] == 'Development Corporation':
        return create_local_authority_key(name['other'])




    elif name['type'] == 'Other':  # 'varnam A' or 'varnam B'
        #return remove_non_alphanumeric(name['other'].upper())

    elif name['type'] == 'Complex Name':
        pass

    elif name['type'] == 'Null Complex Name':
        pass



# Otherwise its a complex name.
# If number is 9999924, treat as varnam A or B



# NB:


name = {
    'type': 'Limited Company',
    'company': 'The Brown Brothers Guardians of the Light Limited Company'
}

cursor = connect(cursor_factory=psycopg2.extras.DictCursor)
print(create_registration_key(name))

# NAME_SCHEMA = {
#     'type': 'object',
#     'properties': {
#         'type': {
#             'type': 'string',
#             'enum': [
#                 'Private Individual',
#                 'County Council',
#                 'Parish Council',
#                 'Rural Council',
#                 'Other Council',
#                 'Development Corporation',
#                 'Limited Company',
#                 'Complex Name',
#                 'Other'
#             ]
#         },
#         'private': PRIVATE_INDIVIDUAL_SCHEMA,
#         'local': AUTHORITY_SCHEMA,
#         'other': {'type': 'string'},
#         'company': {'type': 'string'},
#         'complex': COMPLEX_SCHEMA
#     },
#     'required': ['type'],
#     'oneOf': [
#         {'required': ['private']},
#         {'required': ['local']},
#         {'required': ['company']},
#         {'required': ['other']},
#         {'required': ['complex']}
#     ],
#     'additionalProperties': False
# }