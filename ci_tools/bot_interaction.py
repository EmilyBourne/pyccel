import argparse
from git_evaluation_tools import trigger_test, leave_comment

def run_tests(pr_id):
    """
    Run the tests for the pull request.

    Use the GitHub CLI to trigger the tests using the workflow_dispatch
    trigger.

    Parameters
    ----------
    pr_id : int
        The number of the PR.
    """
    tests = ['Pyccel tests',
             'Doc Coverage Action',
             'Python Linting',
             'Pyccel Linting',
             'Spellcheck Action']
    for t in tests:
        trigger_test(pr_id, t)

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

def print_commands(pr_id):
    """
    List the available bot commands.

    Use the GitHub CLI to leave a comment on the pull request listing
    all the commands which the bot makes available.

    Parameters
    ----------
    pr_id : int
        The number of the PR.
    """

    bot_commands = ("This bot reacts to all comments which begin with `@bot`. This phrase can be followed by any of these commands:\n"
            "- `run tests` : Triggers the tests for a draft pull request\n"
            "- `mark as ready` : Adds the appropriate review flag and requests reviews. This command should be used when the PR is first ready for review, or when a review has been answered.\n"
            "- `commands` : Shows this list detailing all the commands which are understood")

    leave_comment(pr_id, bot_commands)

bot_triggers = {'run tests' : run_tests,
                'mark as ready': mark_as_ready,
                'commands' : print_commands}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Call the function to activate the bot')
    parser.add_argument('pr_number', type=int,
                            help='Number of the pull request')
    parser.add_argument('command', type=str,
                            help='The command left in the comment')

    args = parser.parse_args()

    command = args.command.split('@bot')[1].strip()

    bot_triggers.get(command, print_commands)(args.pr_number)
