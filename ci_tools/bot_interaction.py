import argparse
import json
import os
import sys
from git_evaluation_tools import leave_comment, get_status_json, github_cli, get_job_information, check_previous_comments, set_ready

#senior_reviewer = ['yguclu', 'EmilyBourne']
senior_reviewer = ['EmilyBourne']
trusted_reviewers = ['yguclu', 'EmilyBourne', 'ratnania', 'saidctb', 'bauom']

pr_test_keys = ['linux', 'windows', 'macosx', 'coverage', 'docs', 'pylint',
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

def run_tests(pr_id, tests, outputs, event):
    """
    Run the requested tests and leave a comment on the PR.

    Update the outputs to ensure that the requested tests are run.
    Leave a comment on the PR using the GitHub CLI to indicate the relevant
    commit, action and the test status.

    Parameters
    ----------
    pr_id : int
        The number of the PR.

    tests : list of strs
        The tests requested.

    outputs : dict
        The dictionary containing the output of the bot.

    event : dict
        The event payload of the GitHub workflow.
    """
    # Leave a comment to link to the run page
    ref_sha = get_status_json(pr_id, 'headRefOid')
    url = get_run_url(event)
    comment = f"Running tests on commit {ref_sha}, for more details see [here]({url})\n"
    leave_comment(pr_id, comment)

    # Modify the flags to trigger the tests
    if tests == ['pr_tests']:
        tests = pr_test_keys
    for t in tests:
        outputs[f'run_{t}'] = True

    if outputs['run_coverage']:
        outputs['run_linux'] = True

    outputs['status_url'] = event['repository']['statuses_url'].format(sha=ref_sha)

def mark_as_ready(pr_id):
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

    data = get_job_information(event['run_number'])

    ref_sha = get_status_json(pr_id, 'headRefOid')
    url = get_run_url(event)
    comment = f"Ran tests on commit {ref_sha}, for more details see [here]({url})\n"
    passed = True
    for job in data:
        conclusion = job['conclusion']
        name = job['name']
        if conclusion == 'skipped' or name in ('Bot', 'CleanUpBot'):
            continue
        print(conclusion)
        job_passed = (conclusion == 'success')
        icon = ':heavy_check_mark:' if job_passed else ':x:'
        comment += f"- {icon} {name}\n"
        passed &= job_passed

    leave_comment(pr_id, comment, url in last_message)

    return 'success' if passed else 'failure'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Call the function to activate the bot')
    parser.add_argument('gitEvent', type=str,
                        help='File containing the json description of the triggering event')
    parser.add_argument('output', type=str,
                        help='File where the variables should be saved')
    parser.add_argument('run_id', type=int,
                        help='The id of the runner (used to identify the action page)')
    parser.add_argument('cleanup_trigger', type=str, nargs='?', default='',
                        help='The id of the runner (used to identify the action page)')

    args = parser.parse_args()

    # Parse event payload
    with open(args.gitEvent, encoding="utf-8") as event_file:
        event = json.load(event_file)

    # Save run number with event information
    event['run_number'] = args.run_id

    print(event)

    print("FOUND: ",args.cleanup_trigger)

    cleanup_trigger = args.cleanup_trigger

    # Initialise outputs
    outputs = {'run_linux': False,
               'run_windows': False,
               'run_macosx': False,
               'run_coverage': False,
               'run_docs': False,
               'run_pylint': False,
               'run_lint': False,
               'run_spelling': False,
               'run_pickle': False,
               'run_editable_pickle': False,
               'run_pickle_wheel': False,
               'run_linux_anaconda': False,
               'run_windows_anaconda': False,
               'cleanup_trigger': '',
               'python_version': '',
               'BASE': '',
               'REF': '',
               'SHA': ''}

    if cleanup_trigger == 'request_review_status':
        mark_as_ready(pr_id)
        sys.exit()

    elif cleanup_trigger == 'update_test_information':
        # If reporting after run

        pr_id = event['issue']['number']

        result = update_test_information(pr_id, event)
        with open(args.output, encoding="utf-8", mode='a') as out_file:
            print(f"global_state={result}", file=out_file)
        sys.exit()

    elif 'comment' in event and 'pull_request' in event['issue'] and event['comment']['body'].startswith('/bot'):
        # If bot called explicitly

        pr_id = event['issue']['number']

        trusted_user = event['comment']['author_association'] in ('COLLABORATOR', 'CONTRIBUTOR', 'MEMBER', 'OWNER')
        if not trusted_user:
            comments = get_previous_pr_comments(pr_id)
            trusted_user = any(c.body.strip() == '/bot trust user' and c.author in trusted_reviewers for c in comments)

        comment = event['comment']['body']
        command = comment.split('/bot')[1].strip()
        command_words = command.split()

        if command_words[0] == 'run':
            if trusted_user:
                run_tests(pr_id, command_words[1:], outputs, event)
                outputs['cleanup_trigger'] = 'update_test_information'

        elif command_words[0] == 'try':
            if trusted_user:
                run_tests(pr_id, command_words[2:], outputs, event)
                outputs['python_version'] = command_words[1]
                outputs['cleanup_trigger'] = 'update_test_information'

        elif command == 'mark as ready':
            set_ready(pr_id)

        elif command == 'show tests':
            leave_comment(pr_id, message_from_file('show_tests.txt'))

        elif command == 'trust user':
            leave_comment(pr_id, message_from_file('trusting_user.txt'))
            draft = get_status_json(pr_id, 'isDraft')
            if not draft:
                run_tests(pr_id, ['pr_tests'], outputs, event)
                outputs['cleanup_trigger'] = 'request_review_status'

        else:
            leave_comment(pr_id, message_from_file('bot_commands.txt'))

    elif event['action'] == 'opened':
        # If new PR
        pr_id = event['number']

        # Check whether user is new and/or trusted
        trusted_user = event['pull_request']['author_association'] in ('COLLABORATOR', 'CONTRIBUTOR', 'MEMBER', 'OWNER')
        if trusted_user:
            prs = check_previous_contributions(event['repository']['full_name'], event['pull_request']['author_association'])
            new_user = (len(prs) == 0)
        else:
            new_user = True

        # Choose appropriate message to welcome author
        file = 'welcome_newcomer.txt' if new_user else 'welcome_friend.txt'

        leave_comment(pr_id, message_from_file(file) + message_from_file('checklist.txt'))

        # Ensure PR is draft
        if not event['pull_request']['draft']:
            set_draft(pr_id)

        # If unknown user ask for trust approval
        if not trusted_user:
            leave_comment(pr_id, ", ".join(senior_reviewer)+", please can you check if I can trust this user. If you are happy, let me know with `/bot trust user`")

    elif 'pull_request' in event and not event['pull_request']['draft']:
        # If PR is ready for review

        pr_id = event['number']
        trusted_user = event['pull_request']['author_association'] in ('COLLABORATOR', 'CONTRIBUTOR', 'MEMBER', 'OWNER')
        if not trusted_user:
            comments = get_previous_pr_comments(pr_id)
            trusted_user = any(c.body.strip() == '/bot trust user' and c.author in trusted_reviewers for c in comments)

        if trusted_user:
            run_tests(pr_id, ['pr_tests'], outputs, event)
            outputs['cleanup_trigger'] = 'request_review_status'

    else:
        pr_id = None

    if pr_id is not None:
        outputs['BASE'] = get_status_json(pr_id, 'baseRefName')
        outputs['REF'] = f'refs/pull/{pr_id}/merge'

    print(outputs)

    with open(args.output, encoding="utf-8", mode='a') as out_file:
        for o,v in outputs.items():
            print(f"{o}={v}", file=out_file)
