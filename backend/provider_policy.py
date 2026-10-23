"""Configure SDK transport bounds; agent policies and algorithms stay unchanged."""
from google import genai
from google.genai import types

OriginalClient=genai.Client

class BoundedClient(OriginalClient):
    def __init__(self,*args,http_options=None,**kwargs):
        options=types.HttpOptions.model_validate(http_options or {})
        options.timeout=min(options.timeout or 60000,60000)
        options.retry_options=types.HttpRetryOptions(attempts=2,initial_delay=1,max_delay=3)
        super().__init__(*args,http_options=options,**kwargs)

def configure_provider_bounds():
    # Only this independent web server opts in. Streamlit/tests outside backend
    # keep their original configuration and no key is created or copied.
    genai.Client=BoundedClient
