import argparse
import json
import os
import sys
from git_evaluation_tools import leave_comment, get_status_json

#senior_reviewer = ['yguclu', 'ebourne']
senior_reviewer = ['ebourne']

comment_folder = os.path.join(os.path.dirname(__file__), 'bot_messages')

def run_tests(pr_id, event, outputs):
    """
    Run the tests for the pull request.

    Use the GitHub CLI to trigger the tests using the workflow_dispatch
    trigger.

    Parameters
    ----------
    pr_id : int
        The number of the PR.
    """
    pass
    #if new_user:
    #    comments = get_previous_pr_comments(pr_id)
    #    validated = any(c.body == '/bot trust user' and c.author in senior_reviewer for c in comments)
    #    if not validated:
    #        tags = ", ".join(f"@{r}" for r in senior_reviewer)
    #        message = (tags+
    #                   ", a new user wants to run tests. "
    #                   "Please could you take a quick look and make sure I'm not going to run anything malicious. "
    #                   "If all's ok then let me know with `/bot trust user`. Thanks")
    #        leave_comment(pr_id, message)
    #        return

    #tests = ['Pyccel tests',
    #         'Doc Coverage Action',
    #         'Python Linting',
    #         'Pyccel Linting',
    #         'Spellcheck Action']
    #head_ref = get_head_ref(pr_id)
    #for t in tests:
    #    trigger_test(pr_id, t, head_ref)

def mark_as_ready(pr_id, event, outputs):
    """
    Mark the pull request as ready for review.

    Use the GitHub CLI to check if the PR is really ready for review.
    If this is the case then the correct flag is added and the draft
    status is removed.

    In order to be considered ready for review the PR must:
    - Have all tests passing
    - Have a non-trivial description

    Parameters
    ----------
    pr_id : int
        The number of the PR.
    """
    pass

def print_commands(pr_id, event, outputs):
    """
    List the available bot commands.

    Use the GitHub CLI to leave a comment on the pull request listing
    all the commands which the bot makes available.

    Parameters
    ----------
    pr_id : int
        The number of the PR.
    """

    bot_commands = ("This bot reacts to all comments which begin with `/bot`. This phrase can be followed by any of these commands:\n"
            "- `run tests` : Triggers the tests for a draft pull request\n"
            "- `mark as ready` : Adds the appropriate review flag and requests reviews. This command should be used when the PR is first ready for review, or when a review has been answered.\n"
            "- `trust user` : When written by a senior developer this allows the bot to run tests for a new contributor\n"
            "- `commands` : Shows this list detailing all the commands which are understood")

    leave_comment(pr_id, bot_commands)

def welcome(pr_id, event):
    pass

bot_triggers = {'run tests' : run_tests,
                'mark as ready': mark_as_ready,
                'trust user': lambda pr_id, new_user: None,
                'commands' : print_commands}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Call the function to activate the bot')
    parser.add_argument('gitEvent', metavar='gitEvent', type=str,
                        help='File containing the json description of the triggering event')
    parser.add_argument('output', metavar='output', type=str,
                        help='File where the variables should be saved')

    args = parser.parse_args()

    with open(args.gitEvent, encoding="utf-8") as event_file:
        event = json.load(event_file)

    if 'comment' in event and 'pull_request' in event['issue'] and event['comment']['body'].startswith('/bot'):
        pr_id = event['issue']['number']
        event_name = 'comment'
    elif 'pull_request' in event:
        pr_id = event['number']
        event_name = 'pull_request'
    else:
        pr_id = None
        event_name = None

    if event['action'] == 'opened':
        new_user = event['pull_request']['author_association'] in ('COLLABORATOR', 'FIRST_TIME_CONTRIBUTOR')
        if new_user:
            with open(os.path.join(comment_folder, 'welcome_newcomer.txt')) as msg_file:
                comment = msg_file.read()
        else:
            with open(os.path.join(comment_folder, 'welcome_friend.txt')) as msg_file:
                comment = msg_file.read()
        with open(os.path.join(comment_folder, 'checklist.txt')) as msg_file:
            comment += msg_file.read()

        leave_comment(pr_id, comment)
        sys.exit()


    outputs = {'run_linux': False,
               'run_windows': False,
               'run_macosx': False,
               'run_coverage': False,
               'run_docs': False,
               'run_pylint': False,
               'run_lint': False,
               'run_spelling': False,
               'HEAD': ''
               'REF': ''}

    if pr_id is not None:
        status = get_status_json(pr_id, 'headRefOid,baseRefName,isDraft,comments,reviews,mergeCommit')
        ref = status['headRefOid']
        mergeCommit = status['potentialMergeCommit']
        outputs['HEAD'] = status['baseRefName']
        outputs['REF'] = f'+{merge_commit}:refs/remotes/pull/{pr_id}/merge'

        if event_name == 'comment':
            command = args.command.split('/bot')[1].strip()

            bot_triggers.get(command, print_commands)(args.pr_number, event, outputs)

    print(event)

    with open(args.output, encoding="utf-8", mode='a') as out_file:
        for o,v in outputs.items():
            print(f"{o}={v}", file=out_file)
