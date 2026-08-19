from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status

class SlotUnavailableError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The requested slot is already taken."
    default_code = 'slot_unavailable'

class InvalidOperationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Operation not allowed."
    default_code = 'invalid_operation'

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        # Wrap error in a consistent format
        response.data = {
            'error': response.data.get('detail', str(response.data))
        }
    return response