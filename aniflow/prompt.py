import inquirer

KEY = "KEY"


def confirm(message, default=True):
    return inquirer.prompt(
        [
            inquirer.Confirm(
                KEY,
                message=message,
                default=default,
            )
        ],
        raise_keyboard_interrupt=True,
    ).get(KEY)


def list(message, choices):
    return inquirer.prompt(
        [inquirer.List(KEY, message=message, choices=choices, carousel=True)],
        raise_keyboard_interrupt=True,
    ).get(KEY)


def text(message):
    return inquirer.prompt(
        [
            inquirer.Text(
                KEY,
                message=message,
            )
        ],
        raise_keyboard_interrupt=True,
    ).get(KEY)
