import inquirer

KEY = "KEY"


def confirm(message, default=True):
    return _prompt(
        inquirer.Confirm(
            KEY,
            message=message,
            default=default,
        )
    )


def list(message, choices):
    return _prompt(inquirer.List(KEY, message=message, choices=choices, carousel=True))


def password(message):
    return _prompt(inquirer.Password(KEY, message=message, echo=""))


def _prompt(question):
    return inquirer.prompt([question], raise_keyboard_interrupt=True).get(KEY)
