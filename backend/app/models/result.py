def model_success(message: str, **data):
    return {
        "success": True,
        "message": message,
        "data"   : data,
    }


def model_failure(message: str, **data):
    return {
        "success": False,
        "message": message,
        "data"   : data,
    }
