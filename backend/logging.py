import logging

class CustomFormatter(logging.Formatter):
    def formatException(self, exc_info):
        # Extract the exception type and message
        exc_type, exc_value, _ = exc_info
        return f"{exc_type.__name__}: {exc_value}"

    def format(self, record):
        if record.exc_info is None:
            return super().format(record)

        log_message = f"[{record.levelname}] - {record.asctime} {record.filename} {record.funcName} {record.getMessage()} - {self.formatException(record.exc_info)}"
        return log_message
        