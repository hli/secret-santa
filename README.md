# Secret Santa Supplier

Script to generate and email secret santa assignments.

Config format (see `example.cfg`):

    administrator_gmail
    administrator_gmail_password
    person_id, name, email, [assignment_exclusions]
    person_id, name, email, [assignment_exclusions]

To generate and send emails:

    usage: python secret_santa.py config_filename

To generate and print output without sending emails:

    usage: python secret_santa.py -p config_filename
