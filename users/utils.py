import uuid

def generate_random_username():
    return str(uuid.uuid4())

def generate_random_email():
    return f"{uuid.uuid4()}@example.com"