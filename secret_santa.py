"""
Script to generate and email secret santa assignments.

To generate and send emails (additional email content optional):
    usage: python3 secret_santa.py config_filename [email_content_filename]

To generate and print output without sending emails:
    usage: python3 secret_santa.py -p config_filename

Config format:
    administrator_gmail
    administrator_gmail_generated_app_password
    person_id, name, email, (assignment_exclusions)
    person_id, name, email, (assignment_exclusions)
    ...

Example config:
    administrator@gmail.com
    myGmailGeneratedAppPassword
    person_id1, name1, abcd@email.com, (person_id2; person_id3)
    person_id2, name2, abce@email.com, (person_id1; person_id3)
    person_id3, name3, abcf@email.com, (person_id1; person_id2)
    person_id4, name4, abcg@email.com, (person_id5)
    person_id5, name5, abch@email.com, (person_id4)
    person_id6, name6, abci@email.com, ()

Requirements:
    1) each person_id must be unique
    2) commas are used to delimit the configuration fields
    3) semicolons are used to delimit assignment exclusion persons
    5) a person can not be assigned to any persons in their assignment_exclusions

Assumptions:
    1) a person can not be assigned to themself (this does not need to be configured)

Example print assignments:
    Assignment Id: 21f7d68
    name1 will give to name4.
    name3 will give to name5.
    name2 will give to name6.
    name5 will give to name1.
    name4 will give to name2.
    name6 will give to name3.
"""

import random
import smtplib
import sys
import uuid

MAX_ASSIGNMENT_UUID_LENGTH = 7
MAX_ASSIGNMENT_ATTEMPTS = 3
ADMINISTRATOR_EMAIL_KEY = 'administrator_email'
ADMINISTRATOR_EMAIL_PASSWORD_KEY = 'administrator_email_password'
PARTICIPANTS_KEY = 'participants'
PARTICIPANT_NAME_KEY = 'name'
PARTICIPANT_EMAIL_KEY = 'email'
PARTICIPANT_ASSIGNMENT_EXCLUSIONS_KEY = 'exclusion_ids'

def parse_config_file(config_filename):
    config = {}
    all_exclusion_ids = set()

    with open(config_filename, 'r') as cfg_file:
        for line_number, line in enumerate(cfg_file):
            if line_number == 0:
                config[ADMINISTRATOR_EMAIL_KEY] = line.strip()
            elif line_number == 1:
                config[ADMINISTRATOR_EMAIL_PASSWORD_KEY] = line
            else:
                if not line.strip():
                    continue

                person_id, name, email, assignment_exclusions = map(str.strip, line.split(','))

                # check exclusion formatting
                if not assignment_exclusions or assignment_exclusions[0] != '(' or assignment_exclusions[-1] != ')':
                    raise Exception("assignment_exclusions=(%s) is not formatted with parentheses in the configuration." % assignment_exclusions)

                # extract exclusions within parentheses as set
                exclusion_ids = set(map(str.strip, assignment_exclusions[1:-1].split(';')))
                if '' in exclusion_ids:
                    exclusion_ids.remove('') # derives from empty parentheses
                exclusion_ids.add(person_id) # a person can not be assigned to themself
                all_exclusion_ids.update(exclusion_ids)

                config.setdefault(PARTICIPANTS_KEY, {})
                if person_id in config[PARTICIPANTS_KEY]:
                    raise Exception("person_id=(%s) has appeared more than once in the configuration." % person_id)

                config[PARTICIPANTS_KEY][person_id] = {
                    PARTICIPANT_NAME_KEY: name,
                    PARTICIPANT_EMAIL_KEY: email,
                    PARTICIPANT_ASSIGNMENT_EXCLUSIONS_KEY: exclusion_ids
                }

    all_participants = set(config[PARTICIPANTS_KEY].keys())
    unknown_exclusion_ids = all_exclusion_ids - all_participants
    if unknown_exclusion_ids:
        raise Exception("Assignment exclusions reference unknown participants=(%s)." % unknown_exclusion_ids)

    if ADMINISTRATOR_EMAIL_KEY not in config:
        raise Exception("Missing administrator email in configuration file.")
    elif ADMINISTRATOR_EMAIL_PASSWORD_KEY not in config:
        raise Exception("Missing administrator email password in configuration file.")
    elif PARTICIPANTS_KEY not in config:
        raise Exception("Missing participants in configuration file.")

    return config

def get_assignments(config):
    participant_data = config[PARTICIPANTS_KEY]

    # randomize order of assignment
    all_participants_randomized = list(participant_data.keys())
    random.shuffle(all_participants_randomized)

    # starts out with all participants
    remaining_participants = set(participant_data.keys())

    # giver mapped to getter
    assignments = {}

    for participant in all_participants_randomized:
        assignment_exclusions = participant_data[participant][PARTICIPANT_ASSIGNMENT_EXCLUSIONS_KEY]
        available_participants = remaining_participants - assignment_exclusions

        if not available_participants:
            return None

        assignment = random.choice(tuple(available_participants))
        remaining_participants.remove(assignment)
        assignments[participant] = assignment

    return assignments

def pretty_print_assignments(assignment_uuid, assignments, config):
    print("Assignment Id: %s" % assignment_uuid)
    for giver, getter in assignments.items():
        print("%s will give to %s." % (config[PARTICIPANTS_KEY][giver][PARTICIPANT_NAME_KEY], config[PARTICIPANTS_KEY][getter][PARTICIPANT_NAME_KEY]))

def get_email_content(email_content_filename):
    if email_content_filename:
        with open(email_content_filename, 'r') as email_content_file:
            email_content = email_content_file.read()
        return email_content

    return None

def generate_administrator_email_message(assignment_uuid, assignments_by_name, administrator_email):
    subject = "Secret Santa Assignments (%s)" % assignment_uuid

    content = ''
    for giver, getter in assignments_by_name.items():
        content += "%s will give to %s.\r\n" % (giver, getter)

    message = 'Subject: {}\n\n{}'.format(subject, content)
    return message

def send_assignment_emails(assignment_uuid, assignments, config, email_content):

    administrator_email = config[ADMINISTRATOR_EMAIL_KEY]
    administrator_password = config[ADMINISTRATOR_EMAIL_PASSWORD_KEY]

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(administrator_email, administrator_password)

    try:
        subject = "Alert: Secret Santa Assignment (%s)" % assignment_uuid

        # send emails to each participant
        assignments_by_name = {}
        for giver, getter in assignments.items():
            giver_name = config[PARTICIPANTS_KEY][giver][PARTICIPANT_NAME_KEY]
            getter_name = config[PARTICIPANTS_KEY][getter][PARTICIPANT_NAME_KEY]
            assignments_by_name[giver_name] = getter_name

            recipient_email = config[PARTICIPANTS_KEY][giver][PARTICIPANT_EMAIL_KEY]
            content = "%s will give to %s." % (giver_name, getter_name)
            if email_content:
                content += "\r\n\r\n%s" % email_content

            message = 'Subject: {}\n\n{}'.format(subject, content)
            server.sendmail(administrator_email, recipient_email, message)
            print("Sent assignment to %s." % recipient_email)

        # send email to administrator with complete assignment mapping
        administrator_email_message = generate_administrator_email_message(assignment_uuid, assignments_by_name, administrator_email)
        server.sendmail(administrator_email, administrator_email, administrator_email_message)
        print("Sent all assignments to %s." % administrator_email)

    except Exception as e:
        print(e)
        raise Exception('Failed to send all e-mails successfully.')
    finally:
        server.quit()

if __name__ == '__main__':
    if len(sys.argv) not in [2, 3]:
        print("To generate and send emails:\n\tusage: python %s config_filename [email_content_filename]" % sys.argv[0])
        print("To generate and print output without emails:\n\tusage: python %s -p config_filename" % sys.argv[0])
        exit(1)
    else:
        if len(sys.argv) == 2:
            config_filename = sys.argv[1]
            should_send_email = True
            email_content_filename = None
        elif sys.argv[1] == '-p':
            config_filename = sys.argv[2]
            should_send_email = False
        else:
            config_filename = sys.argv[1]
            should_send_email = True
            email_content_filename = sys.argv[2]

        config = parse_config_file(config_filename)

        attempts = 0
        assignments = None
        while attempts <= MAX_ASSIGNMENT_ATTEMPTS and not assignments:
            assignments = get_assignments(config)
            attempts += 1

        if not assignments:
            raise Exception("Assignment restrictions cannot be easily met; attempts=%s. Please modify the configuration file." % attempts)

        # global unique identifier for this set of assignments
        assignment_uuid = str(uuid.uuid4().hex[:MAX_ASSIGNMENT_UUID_LENGTH])

        if should_send_email:
            email_content = get_email_content(email_content_filename)
            send_assignment_emails(assignment_uuid, assignments, config, email_content)
        else:
            pretty_print_assignments(assignment_uuid, assignments, config)
