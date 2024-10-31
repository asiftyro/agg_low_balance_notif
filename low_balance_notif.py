import os
import requests
import dotenv
import logging
import os

dotenv.load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
LOG_FILE_PATH = os.path.join(SCRIPT_DIR, "log.log")
signin_data = {"username": f"{os.getenv('LB_APP_USER')}", "password": f"{os.getenv('LB_APP_PASS')}"}
signin_url = os.getenv("LB_URL_SIGNIN")
signout_url = os.getenv("LB_URL_SIGNOUT")
url_agg = os.getenv("LB_URL_AGG")
headers = {
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9,bn-BD;q=0.8,bn;q=0.7",
    "connection": "keep-alive",
    "content-type": "application/json",
    "dnt": "1",
    "host": f"{os.getenv('LB_HEADER_HOST')}",
    "origin": f"{os.getenv('LB_HEADER_ORIGIN')}",
    "referer": f"{os.getenv('LB_HEADER_REFERER')}",
    "xtr-app": f"{os.getenv('LB_HEADER_APP')}",
    "sec-ch-ua": '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36",
}

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename=LOG_FILE_PATH, format="%(asctime)s|%(levelname)s|%(filename)s|%(lineno)d|%(message)s", level=logging.INFO
)

def is_num(txt):
    if not txt: return False
    for s in str(txt):
        if s not in ['0','1','2','3','4','5','6','7','8','9','-','.']:
            return False
    return True

def notify(message):
    if not message:
        return False
    bot_token = os.getenv("LB_HELPDESK_TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("LB_HELPDESK_TELEGRAM_CHANNEL_ID")
    send_msg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={channel_id}&text={message}"
    x = requests.get(send_msg_url)
    return x.json()["ok"] == "True"

def get_limits():
    spreadsheet_id = os.getenv("LB_GSHEET_ID")
    sheet_name = os.getenv("LB_GSHEET_NAME")
    api_key = os.getenv("LB_GSHEET_API_KEY")
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}!A:B?alt=json&key={api_key}'
    response = requests.get(url)
    response.raise_for_status() 
    data = response.json()
    lb_dict = dict()
    if 'values' in data:
        for d in data["values"]:
            if len(d)==2:
                key = d[0].lower().strip()
                val = d[1].strip()
                if (is_num(key) == False) and (is_num(val) == True ):
                    lb_dict[key] = val
    return lb_dict

try:
    logger.info("Scrapping started.")
    # Sign in
    response = requests.post(signin_url, json=signin_data, headers=headers)
    # Update headers with 'authorization' for subsequent requests
    headers["authorization"] = "Bearer " + response.json()["accessToken"]
    # Get balance
    response = requests.get(url_agg, headers=headers)
    balance_data = response.json()
    curr_balance = dict()
    for cb in balance_data["dataList"]:
        curr_balance[str(cb["clientId"]).lower().strip()] = cb["balance"]
    # Sign Out
    response = requests.post(signout_url, headers=headers)
    # Get trigger balance from google sheet
    trigger_balance = get_limits()
    # Prepare message body for telegram channel
    message = ""
    for tb in trigger_balance:
        if (tb  in curr_balance) and( float(curr_balance[tb]) < float(trigger_balance[tb])):
            message += f"\n{str(tb)} : {str(curr_balance[tb])}"
    # send message to telegram channel
    if message:
        notify(message)
        logger.info(message.replace('\n', ' '))    
    logger.info("Scrapping ended.")
except Exception as e:
    logger.error(e)

