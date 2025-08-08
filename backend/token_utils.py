import requests
# import os
from dotenv import load_dotenv

load_dotenv() 

def is_token_valid(base_url, token):
    # client_id_new = os.getenv("CLIENT_ID_NEW")
    print("DEBUG - TOKEN:", token)
    url = f"{base_url}/api/v1/user/profile"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        print("DEBUG - Status Code:", response.status_code)
        print("DEBUG - Response Body:", response.text)

        if response.status_code == 200:
            return True, response.json()  # Return profile data
        elif response.status_code == 401:
            return False, {"error": "Unauthorized - token may be invalid or expired"}
        elif response.status_code == 403:
            return False, {"error": "Forbidden - token valid but lacks access"}
        elif response.status_code == 500:
            return False, {"error": "Server error - try again later"}
        else:
            return False, {"error": f"Unexpected status {response.status_code}", "body": response.text}
       
    except requests.exceptions.Timeout:
        return False, {"error": "Request timed out - check your internet or API server status"}
    except Exception as e:
        return False, {"error": f"Unexpected exception: {str(e)}"}
       

