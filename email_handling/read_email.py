from email.header import decode_header 
import imaplib
import email
import os # for managing attachments
import quopri # for decode_content
import base64 # for decode_content

# class to represent an email message
class Message:
    def __init__(self, from_email, subject, body, date, attachments, references, message_id, mail_id):
        self.from_email = from_email # email of sender
        self.subject = subject # subject header of email
        self.body = body # body content of email
        self.date = date # date the email was sent
        self.attachments = attachments # stores absolute file paths of attachments
        self.references = references # list of message ids in the email thread
        self.message_id = message_id #unique id in email header
        self.mail_id = mail_id # id of mail inside the mailbox

    def __repr__(self):
        return f"Message(from_email={self.from_email}, subject={self.subject}, date={self.date}, references={self.references})"

# function to decode messages into original, readable form => returns decoded body content
def decode_content(content, encoding):
    if encoding == 'quoted-printable':
        return quopri.decodestring(content).decode('utf-8')
    elif encoding == 'base64':
        return base64.b64decode(content).decode('utf-8')
    else:
        # No decoding needed for other schemes
        return content

# function to mark email as seen so it is not processed again => returns nothing
def mark_email_as_seen(imap_host, imap_port, imap_user,  imap_pass, mail_id):
    try:
        # Connect to the IMAP server
        imap_ssl = imaplib.IMAP4_SSL(host=imap_host, port=imap_port)
        imap_ssl.login(imap_user, imap_pass)

        # Select the mailbox (e.g., 'INBOX')
        imap_ssl.select(mailbox='CJDev', readonly=False)

        # Mark the email as seen
        # imap_ssl.uid('STORE', email_id, '+FLAGS', '(\Seen)')
        imap_ssl.store(mail_id, '+FLAGS', '\\Seen') 
        # Logout from the server
        imap_ssl.logout()

        print(f"Email with mail-id {mail_id} marked as seen.")

    except Exception as e:
        print(f"Error marking email as seen: {e}")
        # Handle the error as needed, e.g., logging


# function to retrieve email data in the form of Message Objects => returns a list of Message Objects (From Message Class)
def retrieve_email(imap_host, imap_port, imap_user, imap_pass, mail_box):
    email_messages = []

    # Establish connection to imap server
    try:
        imap_ssl = imaplib.IMAP4_SSL(host=imap_host, port=imap_port)
    except Exception as e:
        print("ErrorType : {}, Error : {}".format(type(e).__name__, e))
        imap_ssl = None

    print("Connection Object : {}".format(imap_ssl))

    # Log in to mailbox
    print("Logging into mailbox...")
    try:
        resp_code, response = imap_ssl.login(imap_user, imap_pass)
    except Exception as e:
        print("ErrorType : {}, Error : {}".format(type(e).__name__, e))
        resp_code, response = None, None

    print("Response Code : {}".format(resp_code))
    print("Response      : {}\n".format(response[0].decode()))

    # Set desired mailbox (in this case messages with the label "CJDev will be chosen")
    imap_ssl.select(mailbox=mail_box, readonly=True)

    # select only unseen/new messages
    criteria = 'UNSEEN'

    # Retrieve Mail IDs for given Directory 
    resp_code, mail_ids = imap_ssl.search(None, criteria)

    #### mail_ids is a list containing only one object -> a bytes object
    print("Mail IDs : {}\n".format(mail_ids[0].decode().split()))

    # Display New Messages for given Directory 
    for mail_id in mail_ids[0].decode().split()[:]:
    
        print("================== Start of Mail [{}] ====================".format(mail_id))

        # Fetch mail data in the RFC 822 format (defines sturcture of email messages)
        resp_code, mail_data = imap_ssl.fetch(mail_id, '(RFC822)') 
        
        #### info about mail_data ####
        #### type: list ####
        #### first element type: tuple of two elements (first element contains key, second element is content of the message) ####

        ## Construct Message from mail
        message = email.message_from_bytes(mail_data[0][1])  
        
        # decoding subject header
        encoded_subject = message.get("Subject")
        decoded_subject_parts = decode_header(encoded_subject) 

        # empty list to store the different parts of subject header
        decoded_subject = []
        for part, encoding in decoded_subject_parts:
            if isinstance(part, bytes):
                # Decode the part using the specified encoding, defaulting to 'utf-8' if encoding is None
                decoded_subject.append(part.decode(encoding if encoding else 'utf-8'))
            else:
                # If part is not bytes, use it as-is
                decoded_subject.append(part)
                
        # Join all parts into a single string
        decoded_subject = ''.join(decoded_subject)

        # log out email info (for testing purposes)
        print("From       : {}".format(message.get("From")))
        print("To         : {}".format(message.get("To")))
        print("Cc         : {}".format(message.get("Cc")))
        print("Bcc        : {}".format(message.get("Bcc")))
        print("Date       : {}".format(message.get("Date")))
        print("Message-ID : {}".format(message.get("Message-ID")))
        print("Subject    : {}".format(decoded_subject))

        # empty list to store the file paths of attachments
        filepaths = []

        # Iterate through each part of the email message
        for part in message.walk():

            # Skip multipart parts as they are containers for other parts
            if part.get_content_maintype() == 'multipart':
                continue
            
            # Process plain text parts of the email
            if part.get_content_type() == "text/plain":

                # Get the raw string representation of the part
                encoded_content=part.as_string()

                # decode the content based on the endocing scheme
                decoded_content=decode_content(encoded_content, part.get('Content-Transfer-Encoding'))

                # Split the decoded content into lines
                body_lines = decoded_content.split("\n")

                # Join the remaining lines back into a single string, separated by newline character
                body_content = "\n".join(body_lines)
                print(body_content) 

                continue
            
            # Skip parts without a content disposition (i.e., not attachments or inline files)
            if part.get('Content-Disposition') is None:
                continue

            # Save attachment into "attachments" folder
            filename = part.get_filename()
            if filename:
                # Define the file path to save the attachment
                filepath = os.path.join('./email_handling/attachments', filename)

                # Open the file in binary write mode and write the decoded payload/content
                with open(filepath, 'wb') as f:
                    f.write(part.get_payload(decode=True))
                
                print(f'Saved attachment: {filename}')

                # Add the absolute file path of the attachment to the filepaths list
                filepaths.append(os.path.abspath(filepath))

        # assign values to attributes of message object ####
        from_email = message.get("From")
        date = message.get("Date")
        subject = decoded_subject
        body = body_content
        attachments = filepaths
        references = message.get("References")
        message_id = message.get("Message-ID")

        ### create message object ###
        email_message = Message(from_email, subject, body, date, attachments, references, message_id, mail_id)
        ### append message object to list of messages
        email_messages.append(email_message)

        print("================== End of Mail [{}] ====================\n".format(mail_id))


    # Close Selected Mailbox 
    imap_ssl.close()

    # Log out of Mailbox 
    print("\nLogging Out....")
    try:
        resp_code, response = imap_ssl.logout()
    except Exception as e:
        print("ErrorType : {}, Error : {}".format(type(e).__name__, e))
        resp_code, response = None, None

    print("Response Code : {}".format(resp_code))
    print("Response      : {}".format(response[0].decode()))

    # returns list of email messages 
    return email_messages