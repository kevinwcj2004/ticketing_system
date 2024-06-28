# finished commenting, code looks clean
# now need to improve error handling
import re # "regular expression" for matching ticket reference_id


# function to create a new customer_id => returns the newly created customer_id
def generate_customer_id(cursor):
    
    find_last_customer_query = "SELECT MAX(customer_id) FROM customers"

    # fetch the last customer_id from the customers table
    cursor.execute(find_last_customer_query)
    last_customer = cursor.fetchone()

    # if last_customer returns None, the last_customer_id will be set to 0
    if last_customer[0] is not None:
        last_customer_id = last_customer[0]
    else : 
        last_customer_id = 0

    # new customer_id increments from the last customer_id by 1
    new_customer_id = last_customer_id + 1

    return new_customer_id

# function to find customer in the customers table or create a new entry => returns the customer_id
def check_or_create_customer(email, cursor):

    find_customer_query = "SELECT customer_id FROM customers WHERE email=%s"
    insert_customer_query = "INSERT INTO customers (customer_id, email) VALUES (%s, %s)"

    # check table for existing customer
    cursor.execute(find_customer_query, (email,))
    customer = cursor.fetchone()

    # create new entry in customers table when customer doesn't exist
    if not customer:
        customer_id = generate_customer_id(cursor)
        cursor.execute(insert_customer_query, (customer_id, email))
    else:
        customer_id = customer[0] 

    return customer_id

# function to create a new ticket_id => returns the newly created ticket_id
def generate_ticket_id(cursor):
    
    find_last_ticket_query = "SELECT MAX(ticket_id) FROM tickets"

    # Fetch the last ticket_id from the tickets table
    cursor.execute(find_last_ticket_query)
    last_ticket = cursor.fetchone()
    
    # if last_ticket returns None, the last_ticket_id will be set to 0
    if last_ticket[0] is not None:
        last_ticket_id = last_ticket[0]
    else:
        last_ticket_id = 0

    # new ticket_id increments from the last ticket_id by 1
    new_ticket_id = last_ticket_id + 1

    return new_ticket_id

# function to obtain the first Message-ID (belongs to the parent email message in the thread) from the References of the current email => returns parent email message-id
def extract_reference_id(references):

    # references is None when the current email is the first email/parent email in the thread
    if references is None:
        return None
    
    # the pattern of a message id is a series of characters enclosed in <>
    reference_id_pattern = r'<[^>]+>'

    # obtain a list of message ids (belongs to all previous emails in the thread)
    reference_ids = re.findall(reference_id_pattern, references)
    
    if reference_ids:
        return reference_ids[0] # return first message-id in the list of message-ids (belong to the parent)

# function to find ticket in the tickets table or create a new entry => returns the ticket_id
def check_or_create_ticket(references, message_id, cursor):

    find_ticket_query = "SELECT ticket_id FROM tickets WHERE reference_id = %s"
    insert_ticket_query = "INSERT INTO tickets (ticket_id, reference_id) VALUES (%s, %s)"

    # obtain the message-id of the parent message in the thread (which will be used as the reference_id in the tickets table)
    parent_message_id = extract_reference_id(references)

    # if parent_message_id exists, current email belongs to a thread
    if parent_message_id:
        cursor.execute(find_ticket_query, (parent_message_id,))
        ticket = cursor.fetchone()

        # return existing ticket_id if ticket already exists
        if ticket:
            return ticket[0] 
    
    # Create a new ticket if reference id is not present in the table
    new_ticket_id = generate_ticket_id(cursor)

    # parent_message_id is not None but is not found in the table means the current email is in a thread, but this thread has not been ticketed
    if parent_message_id:
        new_reference_id = parent_message_id
    
    # parent_message_id is None, meaning this is the parent email, the reference_id will be the message_id of the email itself
    else:
        new_reference_id = extract_reference_id(message_id)

    # insert new ticket into tickets table
    cursor.execute(insert_ticket_query, (new_ticket_id, new_reference_id))

    return new_ticket_id


# function to find customer_ticket pair in the customers_tickets table or create a new entry => returns nothing
def check_or_create_customer_ticket(customer_id, ticket_id, cursor): 

    find_pair_query = "SELECT * FROM customers_tickets WHERE customer_id=%s AND ticket_id=%s"
    insert_pair_query = "INSERT INTO customers_tickets (customer_id, ticket_id) VALUES(%s, %s)"

    # check table for exisitng customer_ticket pair
    cursor.execute(find_pair_query, (customer_id, ticket_id))
    customer_ticket = cursor.fetchone()

    # insert new entry when pair does not exist
    if not customer_ticket:
        cursor.execute(insert_pair_query, (customer_id, ticket_id))


# searches database to check for empty columns in the customers table and tickets table => returns a list containing missing fields
def check_missing_info(customer_id, ticket_id, cursor):

    # the sequence of the field names in the columns list must be the same as in the query statements (for customers_columns[index] & tickets_columnns[index] to work)
    customer_columns = ["name", "phone_number", "company_name"]
    ticket_columns = ["issue_raised", "sales_order_number", "product_service"]

    missing_customer_info = []
    missing_ticket_info = []

    query_ticket = """
    SELECT issue_raised, sales_order_number, product_service
    FROM tickets
    WHERE ticket_id = %s
    """
    query_customer = """
    SELECT name, phone_number, company_name
    FROM customers
    WHERE customer_id = %s
    """

    # search for missing customer fields
    cursor.execute(query_customer, (customer_id,))
    customer = cursor.fetchone()
    if customer:
        for index, value in enumerate(customer):
            # empty field is added into the missing_customer_info list
            if value is None:
                missing_customer_info.append(customer_columns[index])

    # search for missing ticket fields
    cursor.execute(query_ticket, (ticket_id,))
    ticket = cursor.fetchone()
    if ticket:
        for index, value in enumerate(ticket):
            if value is None:
                # empty field is added into the missing_customer_info list
                missing_ticket_info.append(ticket_columns[index])

    # combine two list
    return missing_customer_info + missing_ticket_info


# function to update missing fields in database after email is processed by ai model => returns nothing
def update_info(customer_id, ticket_id, extracted_info, cursor):

    customer_columns = ["name", "phone_number", "company_name"]
    ticket_columns = ["issue_raised", "sales_order_number", "product_service"]
    update_customers_query = "UPDATE customers SET "
    update_tickets_query = "UPDATE tickets SET "
    update_customer_values = []
    update_tickets_values = []
    customers_field_present = False
    tickets_field_present = False
    
    # extracted info is a dictionary containing key-value pairs
    for field, value in extracted_info.items():
        
        # check if the field belongs to customers table
        if field in customer_columns:
            update_customers_query += f"{field} = %s, "
            update_customer_values.append(value)
            customers_field_present = True

        # check if the field belongs to tickets table
        elif field in ticket_columns:
            update_tickets_query += f"{field} = %s, "
            update_tickets_values.append(value)
            tickets_field_present = True
    
    # only execute sql commands when there are customers table values to be inserted 
    if customers_field_present:
        update_customers_query = update_customers_query.rstrip(", ")  # Remove the trailing comma
        update_customers_query += " WHERE customer_id = %s"
        update_customer_values.append(customer_id)
        cursor.execute(update_customers_query, tuple(update_customer_values))

    # only execute sql commands when there are tickets table values to be inserted 
    if tickets_field_present:
        update_tickets_query = update_tickets_query.rstrip(", ")  # Remove trailing comma
        update_tickets_query += " WHERE ticket_id = %s"
        update_tickets_values.append(ticket_id)
        cursor.execute(update_tickets_query, tuple(update_tickets_values))


# temp script to delete all entries in a table
def delete_all_entries(table_names, cursor):

    for table_name in table_names:
        cursor.execute(f"DELETE FROM {table_name}")

