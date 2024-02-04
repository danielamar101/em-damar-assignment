import random
from time import sleep
import datetime

import requests
from flask import Flask,request

#Retrieve up to date SSL scan results for www.elliottmgmt.com from Qualys SSL Labs API documentation is available at (https://github.com/ssllabs/ssllabs-scan/blob/stable/ssllabs-api-docs.md)
#Format relevant information into a report ready for email distribution.

# When you want to obtain fresh test results for a particular host:

# Invoke analyze with the startNew parameter to on. Set all to done.
# The assessment is now in progress. Call analyze periodically (without the startNew parameter!) until the assessment is finished. You can tell by observing the Host.status field for either READY or ERROR values.
# When there are multiple servers behind one hostname, they will be tested one at a time.
# During the assessment, interim responses will contain only endpoint status, but not full information.
# At the end of the assessment, the response will contain all available information; no further API calls will need to be made for that host.
# When you're happy to receive cached information (e.g., in a browser add-on):


app = Flask(__name__)


# scan endpoint looks for a host query parameter
@app.route("/scan")
def hello_world():
    host = request.args.get('host',None)
    if host is not None:
        print(f'Scanning {host}...')
        response, status = fetch_report(host)
        print(f'Host: {host} returned code {status}.')
        return response, status
    else:
        return 'Host query parameter needs to be set!\n', 400


def fetch_report(host):

    api_url = f'https://api.ssllabs.com/api/v2/analyze?host={host}&all=done'

    # startNew on only for initial request
    response = requests.get(f'{api_url}&startNew=on')

    jsonned_response = None
    while jsonned_response is None:
        match response.status_code:
            case 200:
                results = response.json()
                if results['status'] == 'READY':
                    jsonned_response = results
                else:
                    sleep(10)
            case 400:
                return False, 400
            case 429:
                print("You wrote a bad client!")
                return False, 429
            case 503 | 529:
                # between 15-30 min random sleep, keep trying after, as per docs
                sleep(random.randrange(900, 1800))
            case _:
                pass
        
        response = requests.get(api_url)

    details = jsonned_response['endpoints'][0]['details']

    is_revoked =  details['chain']['certs'][0]['revocationStatus'] 
    if is_revoked == 2:
        is_revoked = "Certificate Not Revoked"
    else:
        is_revoked = "Not checked or some other erroneous event occured."
    
    issued_at = datetime.datetime.fromtimestamp(details['cert']['notBefore'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
    is_valid_until = datetime.datetime.fromtimestamp(details['cert']['notAfter']/ 1000).strftime('%Y-%m-%d %H:%M:%S')

    encryption_obj = details['key']
    encryption_readable_string = f'{encryption_obj["alg"]} {encryption_obj["strength"]}'

    issued_by_obj = details['cert']['issuerSubject']
    issued_by_obj = issued_by_obj.split(', ')
    readable_issued_by = {
        'Common Name': issued_by_obj[0].split('=')[1],
        'Organization': issued_by_obj[1].split('=')[1]
    }

    return json_to_bulleted_list({
        'Host': host,
        'Is Exceptional': jsonned_response['endpoints'][0]['isExceptional'],
        'Grade': jsonned_response['endpoints'][0]['grade'],
        'tls_protocol': [protocol['version'] for protocol in details['protocols']],
        'Top Level Cert Revocation Status': is_revoked,
        'Issued At': issued_at,
        'Is Valid Until': is_valid_until,
        'Encrpytion Method': encryption_readable_string,
        'Issued By': readable_issued_by
    }), 200


# print(fetch_report('www.elliottmgmt.com'))

def json_to_bulleted_list(json_obj, indent=0):
    bullets = ""
    indent_str = "  " * indent  
    if isinstance(json_obj, dict): 
        for key, value in json_obj.items():
            bullets += f"{indent_str}- {key}:\n{json_to_bulleted_list(value, indent+1)}"
    elif isinstance(json_obj, list): 
        for item in json_obj:
            bullets += f"{indent_str}- {json_to_bulleted_list(item, indent+1)}"
    else:  # If the item is neither a list nor a dictionary, must be leaf node
        bullets += f"{indent_str}- {json_obj}\n"
    return bullets


if __name__ == '__main__':
    port = 4545
    app.run(host="0.0.0.0", port=port, debug=True)
    print(f"Server is listening on port {port}")