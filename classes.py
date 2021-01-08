import csv
import re
import random
import os


class Error:
    def __init__(self):

        self.error_codes = {
            100: "All OK",
            101: "No nested curly braces",
            102: "Extra closing brace(s)",
            103: "Extra opening brace(s)",
            104: "Minimum 2 sets of braces needed",
            105: "Phrase should contain A and FF as headings",
            106: "Phrase contains empty heading(s)",
            201: "Multiple columns have the same name.",
            203: "Inconsistency - number of items different in each row of the acronym list.",
            204: "Full form not provided: {ff}",
            205: "Empty acronym list",
            206: "Repeats: {repeats}",
            301: "Headings mismatch: Phrase({pH}), Acronyms({aH})",
            302: "Acronyms not present: {acronyms}"
        }

    def display_error(self, error_code, **kwargs):

        if error_code == 206:
            return self.error_codes[error_code].format(repeats=kwargs['repeats'])
        if error_code == 204:
            return self.error_codes[error_code].format(ff=kwargs['ff'])
        if error_code == 301:
            return self.error_codes[error_code].format(pH=kwargs['pH'], aH=kwargs['aH'])
        if error_code == 302:
            return self.error_codes[error_code].format(acronyms=kwargs['acronyms'])

        return self.error_codes[error_code]


class Phrase:

    def __init__(self, *args):

        # use default phrase if the user does not provide one
        if len(args) == 0:
            self.phrase = '{A} stands for {FF}.'
            self.item_count = 2
        else:
            self.phrase = args[0]
            self.item_count = 0

        self.error_handler = Error().display_error
        self.head = []

    # check the phrase for pairs that are matching, not nested and are atleast 2 in number
    def parse(self):

        stack = []

        # to check for nested braces
        last = '}'

        for i in self.phrase:

            if i == '{':

                # if the current as well as last character is same, that means nesting has happened.
                if last == '{':
                    return self.error_handler(101)

                else:
                    stack.append(1)
                    last = '{'

            elif i == '}':

                # if the stack is empty - extra closing brace
                if len(stack) == 0:
                    return self.error_handler(102)
                stack.pop()
                last = '}'

        # if some brace is leftover
        if len(stack) != 0:
            return self.error_handler(103)

        heads = re.findall(r'(?<=\{)(.*?)(?=\})', self.phrase)
        if 'A' not in heads or 'FF' not in heads:
            return self.error_handler(105)

        for heading in heads:
            if heading.strip() == '':
                return self.error_handler(106)

            self.item_count += 1
            self.head.append(heading.strip())

        # if the number of pairs is less than 2 (A, FF are the minimum)
        if self.item_count < 2:
            return self.error_handler(104)

        return self


class Acronym:
    def __init__(self, filename):

        self.acronyms_obj = {}
        self.filename = filename
        self.repeated = {}
        self.missing_ff = {}
        self.head = []
        self.acronyms = set()
        self.ff_index = -1
        self.error_handler = Error().display_error

    # count how many times each acronym repeats
    def check_for_repeats(self, item):

        if item in self.acronyms:
            if item in self.repeated.keys():
                self.repeated[item] += 1
            else:
                self.repeated[item] = 2

    # find which acronyms do not have a corresponding full form
    def check_for_missing_ff(self, row):

        if row[self.ff_index] == '':
            if row[0] in self.missing_ff.keys():
                self.missing_ff[row[0]] += 1
            else:
                self.missing_ff[row[0]] = 2

    def parse(self):

        # refresh the object, just in case same object is used with a different filename
        self.__init__(self.filename)

        with open(self.filename, mode='r') as csv_file:

            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0

            for row in csv_reader:

                # headings row
                if line_count == 0:

                    self.head = row
                    header_count = len(row)

                    # if multiple headings are present
                    if header_count != len(set(self.head)):
                        return self.error_handler(201)

                    # if 'FF' is present
                    if 'FF' in self.head:
                        self.ff_index = self.head.index('FF')
                    else:
                        return self.error_handler(105)

                else:

                    # get the acronym shortform
                    acronym = row[0]

                    # check whether it is a repeat and/or does not have a full form
                    self.check_for_repeats(acronym)
                    self.check_for_missing_ff(row)

                    # create an entry for the acronym
                    self.acronyms_obj[acronym] = {}

                    # if any field is missing
                    if len(row) != header_count:
                        return self.error_handler(203)

                    # add all the heading details
                    # does not start with 1 as the A also has go in the value part
                    for i in range(header_count):
                        self.acronyms_obj[acronym][self.head[i]] = row[i]
                    self.acronyms.add(acronym)

                line_count += 1

        # if the only line was the heading line
        if line_count < 2:
            return self.error_handler(205)

        # if there were any repeats
        if len(self.repeated) > 0:
            return self.error_handler(206, repeats=self.repeated)

        # if there were any missing full forms
        if len(self.missing_ff) > 0:
            return self.error_handler(204, ff=self.missing_ff)

        return self


class Subreddit:

    def __init__(self, name, db):

        self.name = name
        self.db = db
        self.error_handler = Error().display_error

        sub = self.db.find_one(
            {'name': self.name}
        )

        self.phrase = Phrase(sub['phrase']).parse()
        self.headings = sub['headings']
        self.acronym_list = sub['acronym_list']

        self.password = None

    def get_subreddit(self):

        subreddit = self.db.find_one({'name': self.name})
        subreddit.pop('_id')
        self.details = subreddit

        '''
        # convert phrase to a Phrase object
        self.phrase = Phrase(subreddit['phrase']).parse()
        self.opted = subreddit['opted'],
        self.auto = subreddit['auto'],
        self.password = subreddit['password'],
        self.comment_frequency = subreddit['comment'],
        self.heading_count = subreddit['item'],
        self.acronym_list = subreddit['acronym_list']'''

        return self.details

    # only "register" it. no data/preferences
    def insert_subreddit(self, password):

        self.db.insert_one({
            "name": self.name,
            "phrase": Phrase().phrase,
            "password": password,
            "headings": [],
            "acronym_list": {}
        })

        return self.get_subreddit()

    def delete_subreddit(self):
        self.db.delete_one({'name': self.name})

    def delete_all(self):
        self.db.update_one({'name': self.name}, {'$set': {'acronym_list': {}}})

        return True

    def delete_some(self, acronyms):

        present_acronyms = self.acronym_list.keys()
        absent_acronyms = []
        for acronym in acronyms:
            if acronym not in present_acronyms:
                absent_acronyms.append(acronym)

        if len(absent_acronyms) != 0:
            return self.error_handler(302, acronyms=absent_acronyms)

        delete_query_dict = {}

        for acronym in acronyms:
            delete_query_dict['acronym_list.'+acronym] = ""

        self.db.update_one({"name": self.name}, {
                           '$unset': delete_query_dict})

        return True

    def insert_phrase(self, phrase):

        response = Phrase(phrase).parse()

        if not isinstance(response, Phrase):
            return response

        if len(self.headings) > 0:

            compatibility_result = self.acronym_phrase_compatibility(
                self.headings, response.head)

            if compatibility_result != True:
                return compatibility_result

        self.db.update_one(
            {'name': self.name},
            {'$set':
             {
                 'phrase': response.phrase,
                 'headings': response.head
             }
             }
        )

        return True

    def insert_acronyms(self, filename):

        response = Acronym(filename).parse()

        # acronym parse error
        if not isinstance(response, Acronym):
            return response

        compatibility_result = self.acronym_phrase_compatibility(
            response.head, self.phrase.head)

        if compatibility_result != True:
            return compatibility_result

        for key, value in response.acronyms_obj.items():

            self.db.update_one(
                {'name': self.name},
                {'$set':
                    {'acronym_list.'+key: value}
                 }
            )

        return True

    def update_settings(self, stuff):
        self.db.update_one({'name': self.name}, {'$set': stuff})
        return True

    def acronym_phrase_compatibility(self, a_head, p_head):

        # A and FF presence has already been checked while creating these

        if set(a_head) == set(p_head):
            return True

        else:
            return self.error_handler(301, aH=a_head, pH=p_head)

    def get_acronym_file(self, folder):

        filename = self.name+"_acronyms.csv"
        filepath = os.path.join(folder, filename)
        with open(filepath, "w") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.headings)

            writer.writeheader()
            writer.writerows(self.acronym_list.values())

        return filename

    def update_acronym_ff(self, acronym, full_form):

        if acronym not in self.acronym_list.keys():
            return self.error_handler(302, acronyms=acronym)

        print(acronym, full_form)

        self.db.update_one({
            'name': self.name
        }, {
            '$set': {
                'acronym_list.'+acronym+'.'+'FF': full_form
            }
        })

        return True
