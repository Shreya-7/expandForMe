import praw
import pdb
import re
import os
import csv
import pymongo

from classes import Phrase, Acronym, Subreddit

client = pymongo.MongoClient(
    "mongodb+srv://Shreya:MoNgODB@cluster0.dxocy.mongodb.net/<dbname>?retryWrites=true&w=majority")

sub_db = client["acronym_bot"]["subreddit"]
comment_db = client["acronym_bot"]["comment"]
reddit = praw.Reddit('bot1')

disclaimer = "*************** \n\n^(Je suis un bot. Manage settings @ [Bot Website](http://google.com) | [Source Code](https://github.com/Shreya-7/expandForMe))"

comments_replied_to = [i for i in comment_db.distinct(
    'parent_comment_id')]

cursor = sub_db.find({"opted": 1})
subreddits = {}

# finding the names of all the required subreddits
for item in cursor:
    item.pop('_id')
    subreddits[item['name']] = item


# get the subreddit instance of all the required subreddits
subreddit = reddit.subreddit(''.join(subreddits.keys()))

# monitor the continuous stream of comments
for comment in subreddit.stream.comments():

    # if the comment has not been replied to
    if comment.id not in comments_replied_to:

        # if the comment is not my own
        if comment.author.name != 'BookAcronymBot':

            acronyms_done = []
            reply = ''

            # find which sub the comment belongs to
            comment_sub = sub_db.find_one(
                {'name': comment.subreddit.display_name})

            # if auto or if called
            if comment_sub['auto'] == 1 or '!expandForMe' in comment.body:

                # find the initial bot comment - if commented, there must be one entry with the post id
                bot_comment = comment_db.find_one(
                    {'post_id': comment.submission.id})

                if bot_comment is not None:
                    acronyms_done = bot_comment['acronyms_done']

                old_acronym_count = len(acronyms_done)

                # if it has been called, get parent_id
                if '!expandForMe' in comment.body:

                    parent_id = comment.parent_id

                    # if the parent is a comment
                    if parent_id[:3] == 't1_':
                        text_body = reddit.comment(parent_id).body

                    # if the parent is a post
                    else:
                        text_body = reddit.submission(parent_id).body

                else:
                    text_body = comment.body

                for key, value in comment_sub['acronym_list'].items():

                    # if match found
                    if key in text_body:

                        if bot_comment is None or (key not in bot_comment['acronyms_done']):
                            acronyms_done = list(set(acronyms_done + [key]))

                if len(acronyms_done) != old_acronym_count:

                    for acronym in acronyms_done:
                        reply += comment_sub['phrase'].format(
                            **comment_sub['acronym_list'][acronym]) + "\n\n"

                    if bot_comment is None or comment_sub['comment_frequency'] == 1:
                        new_bot_comment = comment.reply(reply+disclaimer)

                    else:
                        reply = bot_comment['comment_body'] + reply
                        new_bot_comment = comment.submission.reply(
                            reply+disclaimer)

                    comment_db.update_one({'post_id': comment.submission.id}, {'$set': {
                        'post_id': comment.submission.id,
                        'parent_comment_id': comment.id,
                        'subreddit_name': comment_sub['name'],
                        'comment_id': [new_bot_comment.id],
                        'comment_body': reply,
                        'acronyms_done': acronyms_done
                    }}, upsert=True)

                    # update the object with the parent comment ID
                    comments_replied_to.append(comment.id)
