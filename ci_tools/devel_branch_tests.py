from bot_tools.bot_funcs import Bot, default_python_versions

if __name__ == '__main__':
    bot = Bot(pr_id = 0)
    for python_version in ('3.7', '3.8', '3.9', '3.10', '3.11'):
        bot.run_tests(['linux'], python_version)
    bot.run_tests(['windows'], '3.7')
    bot.run_tests(['macosx'], '3.9')
    bot.run_tests(['pickle'], '3.8')
    bot.run_tests(['editable_pickle'], '3.8')
    bot.run_tests(['pickle_wheel'], '3.7')
    bot.run_tests(['anaconda_linux'], '3.10')
    bot.run_tests(['anaconda_windows'], '3.10')
