import argparse
import json
import os
import sys
from git_evaluation_tools import leave_comment, get_status_json

#senior_reviewer = ['yguclu', 'ebourne']
senior_reviewer = ['ebourne']

test_keys = ['linux', 'windows', 'macosx', 'coverage', 'docs', 'pylint',
             'lint', 'spelling']

comment_folder = os.path.join(os.path.dirname(__file__), 'bot_messages')

def get_run_url(event):
    """
    Get the URL of the workflow run.

    Use the event information to calculated the URL
    where the results of the workflow can be viewed.

    Parameters
    ----------
    event : dict
        The event payload of the GitHub workflow.

    Results
    -------
    str : The URL.
    """
    url = event['repository']['html_url']
    run_id = event['run_number']
    return f"{url}/actions/runs/{run_id}"

def run_tests(pr_id, command_words, output):
    """
    Run the requested tests and leave a comment on the PR.

    Update the outputs to ensure that the requested tests are run.
    Leave a comment on the PR using the GitHub CLI to indicate the relevant
    commit, action and the test status.

    Parameters
    ----------
    pr_id : int
        The number of the PR.

    command_words : list of strs
        The command issued to the bot.

    output : dict
        The dictionary containing the output of the bot.
    """
    url = get_run_url(events, run_id)
    comment = f"Running tests, for more details see [here]({url}/actions/runs/{run_id})\n"
    tests = command_words[1:]
    if tests == ['all']:
        tests = test_keys
    for t in tests:
        outputs[f'run_{t}'] = True
    leave_comment(pr_id, comment)

def mark_as_ready(pr_id, outputs):
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

def message_from_file(filename):
    """
    Get the message saved in the file.

    Reads the contents of the file `filename`, located in the
    folder ./bot_messages/. The extracted string is returned for
    use as a comment on a PR.

    Parameters
    ----------
    filename : str
        The name of the file to be read

    Results
    -------
    str : The message to be printed.
    """
    with open(os.path.join(comment_folder, filename)) as msg_file:
        comment = msg_file.read()
    return comment

def update_test_information(pr_id, event):
    """
    Update the PR with the information about the tests.

    Use the GitHub CLI to check the results of the tests. If the last
    comment made by the bot was for this set of tests then this comment
    is updated to include the test results. Otherwise a new comment is
    added with the results.

    Parameters
    ----------
    pr_id : int
        The number of the PR.

    event : dict
        The event payload of the GitHub workflow.
    """
    messages, last_message, date = check_previous_comments(pr_id)

    cmd = [github_cli, 'run', 'view', args.run_id, '--json', 'jobs']
    with subprocess.Popen(cmds, stdout=subprocess.PIPE) as p:
        result, _ = p.communicate()
    data = json.loads(result)['jobs']
    print(data)

    url = get_run_url(event)

    comment = f"Ran tests, for more details see [here]({url}/actions/runs/{run_id})\n"
    for job in data:
        conclusion = job['conclusion']
        if conclusion == 'skipped':
            continue
        name = job['name']
        icon = ':heavy_check_mark:' if conclusion == 'completed' else ':x:'
        comment += f"- {icon} {name}\n"

    leave_comment(pr_id, comment, url in last_message)

bot_triggers = {'mark as ready': mark_as_ready,
                'commands' : print_commands}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Call the function to activate the bot')
    parser.add_argument('gitEvent', metavar='gitEvent', type=str,
                        help='File containing the json description of the triggering event')
    parser.add_argument('output', metavar='output', type=str,
                        help='File where the variables should be saved')
    parser.add_argument('run_id', metavar='output', type=int,
                        help='The id of the runner (used to identify the action page)')

    args = parser.parse_args()

    # Parse event payload
    with open(args.gitEvent, encoding="utf-8") as event_file:
        event = json.load(event_file)

    # Save run number with event information
    event['run_number'] = args.run_id

    # Initialise outputs
    outputs = {'run_linux': False,
               'run_windows': False,
               'run_macosx': False,
               'run_coverage': False,
               'run_docs': False,
               'run_pylint': False,
               'run_lint': False,
               'run_spelling': False,
               'HEAD': '',
               'REF': ''}

    if 'comment' in event and 'pull_request' in event['issue'] and event['comment']['body'].startswith('/bot'):
        # If bot called explicitly

        pr_id = event['issue']['number']

        comment = event['comment']['body']
        command = comment.split('/bot')[1].strip()
        command_words = command.split()

        if command_words[0] == 'run':
            run_tests(pr_id, command_words, outputs)

        elif command == 'mark as ready':
            run_tests(pr_id, 'run all', outputs)

        elif command == 'show tests':
            leave_comment(pr_id, message_from_file('show_tests.txt'))

        else:
            leave_comment(pr_id, message_from_file('bot_commands.txt'))

    elif event['action'] == 'opened':
        # If new PR

        new_user = event['pull_request']['author_association'] in ('COLLABORATOR', 'FIRST_TIME_CONTRIBUTOR')
        file = 'welcome_newcomer.txt' if new_user else 'welcome_friend.txt'

        leave_comment(pr_id, message_from_file(file) + message_from_file('checklist.txt'))

        if not event['pull_request']['draft']:
            set_draft(pr_id)

    elif 'pull_request' in event and not event['pull_request']['draft']:
        # If PR is ready for review

        pr_id = event['number']
        run_tests(pr_id, 'run all', outputs)

    elif 'workflow_run' in event and event['action'] == 'completed':
        # If tidying up after previous run

        update_test_information(pr_id, event)

    else:
        pr_id = None

    if pr_id is not None:
        outputs['HEAD'] = get_status_json(pr_id, 'baseRefName')
        outputs['REF'] = f'refs/pull/{pr_id}/merge'

    print(event)

    print(outputs)

    with open(args.output, encoding="utf-8", mode='a') as out_file:
        for o,v in outputs.items():
            print(f"{o}={v}", file=out_file)
