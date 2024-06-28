import requests

def verify_info(response, data_field):
    # temporary, will add more conditions for each data field to filter correct data later
    if response["score"] >= 0.1:
        return True

def extract_info_from_email(missing_info, email_message, API_TOKEN, API_URL):
    API_TOKEN = "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"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    API_URL = "https://api-inference.huggingface.co/models/deepset/roberta-base-squad2"

    def query(payload):
        try:
            response = requests.post(API_URL, headers=headers, json=payload)
            return response.json()
        
        except requests.exceptions.RequestException as err:
            print(f"error has occured in calling api: {err}")
            return False

    #list of data fields required and accompanying questions to be passed to question_answering model 
    fields_questions = {
    "company_name": "What is the name of the company?",
    "name": "What is the name of the individual who sent the email?",
    "sales_order_number": "What is the sales order number?",
    "phone_number": "What is the phone number of the sender?",
    "issue_raised": "What was the issue raised in the email?",
    "product_service": "What is the name of the product or service bought by the customer?"
    }

    successful_call = True
    context = f"Subject: {email_message.subject}\n{email_message.body}"
    extracted_info = {}

    # api call to question answering model using query()
    for field in missing_info:
        response = query(
                    {
                    "inputs": {
                        "question": fields_questions[field],
                        "context": context,
                        }
                    }
                )
        # if there is an error, return immediately 
        if not response:
            successful_call = False
            return missing_info, extracted_info, successful_call
        
        # print answer and confidence score
        print("{}: {:1.5f}".format(response["answer"], response["score"]))

        # verify if data field is present and correct, answer will be added into dictionary
        if verify_info(response, field):
            extracted_info[field] = response["answer"]
            # remove field from missing_info since it has been extracted
            missing_info.remove(field)

    print("-----------------finish calling ai model api-----------------------")
    print(extracted_info)

    return missing_info, extracted_info, successful_call

