from email_handling.read_email import retrieve_email, mark_email_as_seen
from email_handling.db_manip import *
from email_handling.send_email import create_reply_email, send_email
from language_processing.ai_extract_info import extract_info_from_email
from mysql.connector import errorcode
import mysql.connector


# imap configuration
imap_host = 'imap.gmail.com' # or other imap servers
imap_port = 993
imap_user = 'your_email@mail.com'
imap_pass = 'your_email_client_password'
mail_box = "mailbox" # or other tags

# smtp configuration
smtp_host = "smtp.gmail.com" # or other smtp servers
smtp_port = 587
smtp_user = 'your_email@mail.com'
smtp_pass = 'your_email_client_password'

# mysql database configuration
db_config = {
    'user': 'your_db_user_name',
    'password': 'your_db_password',
    'database': 'your_db_name',
}

# ai model inference api configuration
api_token = "your_inference_api_token" 
api_url = "https://api-inference.huggingface.co/models/deepset/roberta-base-squad2"


#retrieve new email message(from_email, subject, body, date, attachments, reference_id, message_id, mail_id)
email_messages = retrieve_email(imap_host, imap_port, imap_user, imap_pass)
print(email_messages)

try:
    # establish connection with database
    db_cnx = mysql.connector.connect(**db_config)

    for email_message in email_messages:

        try: 
            with db_cnx.cursor() as cursor:
                # check or create new customer entry
                customer_id = check_or_create_customer(email_message.from_email, cursor)

                # check or create new ticket entry
                ticket_id = check_or_create_ticket(email_message.references, email_message.message_id, cursor)

                # check or create new customer_id & ticket_id pair 
                check_or_create_customer_ticket(customer_id, ticket_id, cursor)

                # check for missing information (before running ai model)
                missing_info = check_missing_info(customer_id, ticket_id, cursor)

                # extract missing information using ai model
                updated_missing_info, extracted_info, successful_call = extract_info_from_email(missing_info, email_message, api_token, api_url)

                # skip email processing if ai_api call fails
                if not successful_call:
                    print("AI model call failed, skipping email processing.")
                    db_cnx.rollback()
                    continue

                # update extracted info in customers & tickets table
                update_info(customer_id, ticket_id, extracted_info, cursor)

                # craft response email to request for missing info
                reply_email_message = create_reply_email(email_message, updated_missing_info, smtp_user)
                print(reply_email_message)

                # send email using smtp server
                email_sent = send_email(smtp_host, smtp_port, smtp_user, smtp_pass, reply_email_message)

                # mark email as seen and commit data to database once email is sent successfully
                if email_sent:
                    mark_email_as_seen(imap_host, imap_port, imap_user, imap_pass, email_message.mail_id)
                    db_cnx.commit()

                # rollback all changes to the database if email failes to send
                else:
                    db_cnx.rollback()
                
        except Exception as e:
            print(f"Error occured during processing of email: {e}")
            db_cnx.rollback()


except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
    else:
        print(err)
finally:
    db_cnx.close()