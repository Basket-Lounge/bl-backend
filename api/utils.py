import uuid

class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self.json_data = json_data

    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception()

    def json(self):
        return self.json_data
    
def is_valid_uuid(uuid_to_test: str, version : int = 4) -> bool:
    """
    Check if uuid is valid.

    Args:
        uuid_to_test (str): The uuid to test.
        version (int): The version of the uuid. Defaults to 4.
    Returns:
        bool: True if the uuid is valid, False otherwise.
    """

    try:
        uuid.UUID(uuid_to_test, version=version)
        return True
    except ValueError:
        return False