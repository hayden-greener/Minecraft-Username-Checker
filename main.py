import os
import random
import requests
import time
import json
import logging
from typing import List, Dict, Tuple

# Configuration variables
USERNAMES = os.environ.get("MINECRAFT_USERNAMES", "").split(",")
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
DISCORD_USER_ID = os.environ.get("DISCORD_USER_ID", "")

MOJANG_API_RATE_LIMIT = int(os.environ.get("MOJANG_API_RATE_LIMIT", 60))
DISCORD_API_RATE_LIMIT = int(os.environ.get("DISCORD_API_RATE_LIMIT", 300))
INITIAL_DELAY = int(os.environ.get("INITIAL_DELAY", 0))
THIRTY_DAY_DELAY = int(os.environ.get("THIRTY_DAY_DELAY", 2592000))
THIRTY_SEVEN_DAY_DELAY = int(os.environ.get("THIRTY_SEVEN_DAY_DELAY", 3196800))
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", 3600))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", 5))
MAX_USERNAMES = int(os.environ.get("MAX_USERNAMES", 100))
MAX_MESSAGE_LENGTH = int(os.environ.get("MAX_MESSAGE_LENGTH", 2000))
MAX_DISCORD_NOTIFICATIONS = int(os.environ.get("MAX_DISCORD_NOTIFICATIONS", 10))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Message formats
MESSAGE_FORMATS = {
    "initial": [
        "ALERT: {username_str} is now available on Minecraft! The original owner has 37 days to reclaim it.",
        "ATTENTION: {username_str} is available on Minecraft but subject to the 37-day grace period. Keep an eye on it!",
    ],
    "thirty_day": [
        "UPDATE: It's been 30 days since {username_str} became available. The original owner has 7 more days to reclaim it.",
        "REMINDER: {username_str} is still available on Minecraft. The 37-day grace period ends in 7 days.",
    ],
    "thirty_seven_day": [
        "FINAL CALL: The 37-day grace period for {username_str} has ended. It's now fully available for claiming!",
        "LAST CHANCE: {username_str} is permanently available on Minecraft! Grab it now!",
    ],
}

def is_username_available(username: str) -> bool:
    try:
        response = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{username}", timeout=REQUEST_TIMEOUT)
        return response.status_code == 404
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking username availability for {username}: {str(e)}")
        return False

def send_discord_notification(webhook_url: str, message: str) -> None:
    payload = {"content": message}
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=REQUEST_TIMEOUT)
        
        if response.status_code != 204:
            logger.warning(f"Failed to send Discord notification. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending Discord notification: {str(e)}")

def get_random_message(discord_user_id: str, usernames: List[str], message_type: str) -> str:
    num_usernames = len(usernames)
    username_str = ', '.join(usernames)
    url = "https://www.minecraft.net/en-us/msaprofile/mygames/editprofile"
    mention = f"<@{discord_user_id}>"
    
    message = random.choice(MESSAGE_FORMATS[message_type]).format(username_str=username_str)
    
    if num_usernames > 1:
        message = message.replace("is", "are").replace("it", "them")
        
    namemc_links = '\n'.join(f"<https://namemc.com/search?q={username}>" for username in usernames)
    
    full_message = f"{message}\n{url}\n{namemc_links}\n||{mention}||"
    return full_message[:MAX_MESSAGE_LENGTH]

def load_available_usernames(file_path: str) -> Dict[str, int]:
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_available_usernames(available_usernames: Dict[str, int], file_path: str) -> None:
    try:
        with open(file_path, 'w') as file:
            json.dump(available_usernames, file, indent=2)
    except IOError as e:
        logger.error(f"Error saving available usernames: {str(e)}")

def check_usernames(usernames: List[str], webhook_url: str, discord_user_id: str, available_usernames_file: str) -> Tuple[List[str], List[str]]:
    available_usernames = load_available_usernames(available_usernames_file)
    newly_available = []
    taken_usernames = []
    
    for username in usernames:
        if is_username_available(username):
            if username not in available_usernames:
                newly_available.append(username)
                available_usernames[username] = int(time.time())
        else:
            taken_usernames.append(username)
            
    if newly_available:
        message = get_random_message(discord_user_id, newly_available, "initial")
        send_discord_notification(webhook_url, message)
                
    save_available_usernames(available_usernames, available_usernames_file)
    return newly_available, taken_usernames

def check_grace_period(webhook_url: str, discord_user_id: str, available_usernames_file: str, all_taken_usernames: List[str]) -> None:
    available_usernames = load_available_usernames(available_usernames_file)
    current_time = int(time.time())
    
    initial_stage = []
    thirty_day_stage = []
    thirty_seven_day_stage = []
    taken_usernames = []
    
    for username, start_time in list(available_usernames.items()):
        elapsed_time = current_time - start_time
        
        if elapsed_time < THIRTY_DAY_DELAY:
            initial_stage.append(username)
        elif THIRTY_DAY_DELAY <= elapsed_time < THIRTY_SEVEN_DAY_DELAY:
            thirty_day_stage.append(username)
        else:
            if is_username_available(username):
                thirty_seven_day_stage.append(username)
            else:
                taken_usernames.append(username)
                del available_usernames[username]
                
    if thirty_day_stage:
        message = get_random_message(discord_user_id, thirty_day_stage, "thirty_day")
        send_discord_notification(webhook_url, message)
            
    if thirty_seven_day_stage:
        message = get_random_message(discord_user_id, thirty_seven_day_stage, "thirty_seven_day")
        
        for _ in range(MAX_DISCORD_NOTIFICATIONS):
            send_discord_notification(webhook_url, message)
            time.sleep(60)
                
    save_available_usernames(available_usernames, available_usernames_file)
    
    log_status(initial_stage, thirty_day_stage, thirty_seven_day_stage, taken_usernames, available_usernames, all_taken_usernames)

def log_status(initial_stage: List[str], thirty_day_stage: List[str], thirty_seven_day_stage: List[str],
               taken_usernames: List[str], available_usernames: Dict[str, int], all_taken_usernames: List[str]) -> None:
    logger.info("=" * 80)
    logger.info("Minecraft Username Checker Status".center(80))
    logger.info("=" * 80)
    
    logger.info("\nTaken Usernames:")
    for username in all_taken_usernames:
        logger.info(f"- {username}")
    
    logger.info("\nInitial Stage (0-30 days):")
    for username in initial_stage:
        days_left, hours_left, minutes_left = get_time_left(THIRTY_DAY_DELAY, available_usernames[username])
        logger.info(f"- {username} (Days left: {days_left}, Hours left: {hours_left}, Minutes left: {minutes_left})")
        
    logger.info("\n30-Day Stage (30-37 days):")
    for username in thirty_day_stage:
        days_left, hours_left, minutes_left = get_time_left(THIRTY_SEVEN_DAY_DELAY, available_usernames[username])
        logger.info(f"- {username} (Days left: {days_left}, Hours left: {hours_left}, Minutes left: {minutes_left})")
        
    logger.info("\n37-Day Stage (Available for claiming):")
    for username in thirty_seven_day_stage:
        logger.info(f"- {username}")
        
    logger.info("=" * 80)

def get_time_left(delay: int, start_time: int) -> Tuple[int, int, int]:
    time_left = delay - (int(time.time()) - start_time)
    days_left = time_left // 86400
    hours_left = (time_left % 86400) // 3600
    minutes_left = (time_left % 3600) // 60
    return days_left, hours_left, minutes_left

def main() -> None:
    available_usernames_file = os.environ.get("AVAILABLE_USERNAMES_FILE", "/app/available_usernames.json")
    build_mode = os.environ.get("BUILD", "0") == "1"
    
    mojang_api_requests = 0
    discord_api_requests = 0
    all_taken_usernames = []
    
    time.sleep(INITIAL_DELAY)
    
    while True:
        try:
            if mojang_api_requests >= MOJANG_API_RATE_LIMIT:
                time.sleep(60)
                mojang_api_requests = 0
                
            newly_available, taken_usernames = check_usernames(USERNAMES, WEBHOOK_URL, DISCORD_USER_ID, available_usernames_file)
            all_taken_usernames.extend(taken_usernames)
            all_taken_usernames = list(set(all_taken_usernames))
            mojang_api_requests += 1
            
            if discord_api_requests >= DISCORD_API_RATE_LIMIT:
                time.sleep(60)
                discord_api_requests = 0
                
            check_grace_period(WEBHOOK_URL, DISCORD_USER_ID, available_usernames_file, all_taken_usernames)
            discord_api_requests += 1
            
            if build_mode:
                logger.info("Build mode enabled. Exiting after one pass.")
                break
            
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            logger.exception(f"An unexpected error occurred: {str(e)}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()