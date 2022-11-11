# Secret Santa Supplier

Script to generate and email secret santa assignments.

Config format (see `example.cfg`):

    administrator_gmail
    administrator_gmail_password
    person_id, name, email, (assignment_exclusions)
    person_id, name, email, (assignment_exclusions)

To generate assignments and send emails with assignment information to each participant (additional email content optional):

    usage: python secret_santa.py config_filename [email_content_filename]

To generate assignments and print output without sending emails:

    usage: python secret_santa.py -p config_filename
