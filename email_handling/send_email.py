import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from email.header import Header


def create_reply_email(original_email, missing_info, smtp_user):
    # Create a multipart message
    reply_message = MIMEMultipart()

    # Set email headers
    reply_message['From'] = formataddr((str(Header('Kevin WCJ', 'utf-8')), smtp_user))
    reply_message['To'] = original_email.from_email
    reply_message['Subject'] = f"{original_email.subject}"
    reply_message['In-Reply-To'] = original_email.message_id
    if original_email.references:
        reply_message['References'] = f"{original_email.references} {original_email.message_id}"
    # if message received has no references, original email is the parent email, our reply email should only reference the message-id of the parent email
    else:
        reply_message['References'] = f"{original_email.message_id}"
    
    # Create the body of the message (can customize more later on)
    missing_fields = "\n".join([f"- {field}" for field in missing_info])
    body = f"Dear Customer,\n\nWe need the following information to proceed:\n{missing_fields}\n\nThank you."
    
    # Attach the body with the reply_message instance
    reply_message.attach(MIMEText(body, 'plain'))
    
    return reply_message

# function to send email using smtp => returns whether email was successfully sent (true or false)
def send_email(smtp_host, smtp_port, smtp_user, smtp_pass, msg):
    email_sent = False
    try:
        # Connect to SMTP server
        server = smtplib.SMTP(smtp_host, smtp_port)
        # Start TLS (Transport Layer Security) encryption for the SMTP session
        server.starttls()
        # Log in to the SMTP server using provided credentials
        server.login(smtp_user, smtp_pass)
        # Send the email
        server.sendmail(smtp_user, msg['To'], msg.as_string())
        # Terminate the SMTP session and close the connection
        server.quit()
        print("Email sent successfully!")
        # If no exception occurred, set email_sent to True
        email_sent = True

    except Exception as e:
        # Print any exception that occurs during the email sending process
        print(f"Failed to send email: {e}")
    
    return email_sent

