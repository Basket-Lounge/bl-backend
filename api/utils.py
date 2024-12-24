class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self.json_data = json_data

    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception()

    def json(self):
        return self.json_data