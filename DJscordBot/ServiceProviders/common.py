from typing_extensions import Self

class CommonResponseData():
    def __init__(self, provider: str, provider_api_id: str, request_data, inferred_type: str = None):
        self.provider = provider
        self.provider_api_id = provider_api_id
        self.data = request_data
        self.inferred_type = inferred_type
    
    @staticmethod
    def create_empty():
        return CommonResponseData('none', '0', {})
    
    def apply_values(self, other_response_data: Self):
        self.provider = other_response_data.provider
        self.provider_api_id = other_response_data.provider_api_id
        self.data = other_response_data.data
        self.inferred_type = other_response_data.inferred_type

    def __str__(self):
        return f"RequestData from [{self.provider}] API of element with provider ID of '{self.provider_api_id}'"