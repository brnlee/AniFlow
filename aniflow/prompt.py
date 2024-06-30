import inquirer

KEY = "KEY"


def prompt(question):
    return inquirer.prompt([question], raise_keyboard_interrupt=True).get(KEY)


def confirm(message, default=True):
    return prompt(
        inquirer.Confirm(
            KEY,
            message=message,
            default=default,
        )
    )


def list(message, choices):
    return prompt(inquirer.List(KEY, message=message, choices=choices, carousel=True))


def password(message):
    return prompt(inquirer.Password(KEY, message=message, echo=""))
