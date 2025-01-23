import logging
import sys
import os
from pprint import pprint
import requests
from nodriver.cdp.network import clear_browser_cookies
import time
from utils import get_data_by_date, format_fdata, get_data_from_sheet
from sheets_api import get_data_from_range, get_data_from_google_sheets
import nodriver as uc
from nodriver.core import element
from nodriver import Tab, cdp, Element, Browser, start
from nodriver.cdp.dom import Node
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

API_KEY = 'http://local.adspower.net:50325'

# Define custom log levels
SUCCESS = 25
FAILURE = 35
INFO = 20
logging.addLevelName(SUCCESS, "SUCCESS")
logging.addLevelName(FAILURE, "FAILURE")
logging.addLevelName(INFO, 'INFO')

# Configure logger
class CustomFormatter(logging.Formatter):
    # Colors using colorama
    grey = Fore.LIGHTBLACK_EX
    green = Fore.GREEN
    yellow = Fore.YELLOW
    red = Fore.RED
    bold_red = Fore.RED + Style.BRIGHT
    blue = Fore.CYAN
    reset = Style.RESET_ALL

    # Format strings for different parts of the log
    log_format = "{time_color}%(asctime)s{reset} [{level_color}%(levelname)s{reset}] {msg_color}%(message)s{reset}"

    FORMATS = {
        logging.DEBUG: log_format.format(time_color=blue, level_color=grey, msg_color=grey, reset=reset),
        logging.INFO: log_format.format(time_color=blue, level_color=grey, msg_color=yellow, reset=reset),
        SUCCESS: log_format.format(time_color=blue, level_color=green, msg_color=yellow, reset=reset),
        INFO: log_format.format(time_color=blue, level_color=grey, msg_color=yellow, reset=reset),
        logging.WARNING: log_format.format(time_color=blue, level_color=red, msg_color=yellow, reset=reset),
        logging.ERROR: log_format.format(time_color=blue, level_color=red, msg_color=yellow, reset=reset),
        FAILURE: log_format.format(time_color=blue, level_color=bold_red, msg_color=yellow, reset=reset),
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%H:%M:%S')
        return formatter.format(record)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)


def ads_request(API_KEY, endpoint='/'):
    while True:
        resp = requests.get(API_KEY + endpoint).json()
        if resp["code"] != 0:
            if resp["msg"] == 'Too many request per second, please check':
                time.sleep(1)
            else:
                logger.error(f"{resp['msg']}")
                logger.error("Please check ads_id")
                return None
        else:
            return resp


async def main(config, data, adspower_api=None):
    driver = await uc.Browser.create(config=config)
    retries = 3
    print(data['dob'], type(data['dob']))
    dob_parts = data['dob'][5:-1].split(',')
    year, month, day = dob_parts
    
    day = day
    month = str(int(month) + 1)
    print(day, month, year)
    for attempt in range(retries):
        page = await driver.get('https://mail.google.com/mail/u/0/#inbox')
        isValid = None
        noValid = False
        loading = 0
        while await page.evaluate('document.readyState') == 'loading': 
            if loading == 60: break
            time.sleep(1)
            loading += 1
        await page.activate()
        try:
            await page.wait_for(f'div[data-email=\"{data["email"]}\"]', timeout=5)
            noValid = True  
        except: pass

        try:
            await page.wait_for(f'a[aria-label*=\"{data["email"]}\"]', timeout=5)
        except: noValid = True

        if noValid: break


        await page.get('https://www.uefa.com/')
        loading = 0
        while await page.evaluate('document.readyState') == 'loading': 
            if loading == 120: break
            time.sleep(1)
            loading += 1
        if loading == 120: 
            logger.info(f"Спроба {attempt + 1} перезавантажити сторінку")
            continue
        
        # REGISTRATION LOGIC HERE
        try: 
            await page.activate()
            try:
                cookie_button = await page.wait_for('button[id="onetrust-reject-all-handler"]', timeout=120)
                await cookie_button.mouse_click()
            except: pass
            login_button = await page.wait_for(f'body > div.main-wrap > div > div > div.navigation.navigation--sticky.d3-plugin > div.d3-react.navigation-wrapper.navigation--corporate.pk-theme--dark > nav > div.pk-d--flex.pk-align-items--center.pk-ml--s > pk-button', timeout=120)
            await login_button.mouse_click()
            google_button = await page.wait_for(f'div[aria-label="Sign in with Google"]', timeout=120)
            await google_button.mouse_click()
            try:
                temp_gmail_tab = driver.tabs[-1]
                body = await temp_gmail_tab.select(f'div[data-email=\"{data["email"]}\"]')
                await body.mouse_click()
                
                gmail_continue_button = await temp_gmail_tab.wait_for(f'div > div > div:nth-child(2) > div > div > button > span', timeout=120)
                await gmail_continue_button.mouse_click()
                time.sleep(1)
            except: pass
            await page.activate()

            try:
                password_input = await page.wait_for('#gigya-password-107949133340454600', timeout=120)
                await password_input.send_keys(data['uefa_password'])
                submit_button = await page.wait_for('#gigya-link-accounts-form > div:nth-child(3) > div > div:nth-child(3) > div > div > input', timeout=120)
                await submit_button.mouse_click()
            except: 
                await page.reload()
                logger.info(f"Спроба {attempt + 1} перезавантажити сторінку")
            
            pincode = False
            try: pincode = await page.wait_for('#gigya-custom-pin-code-container', timeout=120)
            except: pass
            
            if not pincode:
                await page.reload()
                logger.info(f"Спроба {attempt + 1} перезавантажити сторінку")
                # await page.evaluate('document.cookie.split(";").forEach(cookie => document.cookie = cookie.trim().replace(/=.*/, "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/"));')
                continue

            # GOOGLE PINCODE PART
            
            page2 = await driver.get('https://mail.google.com/mail/u/0/#inbox', new_tab=True)
            is_authenticated = False

            message = False
            for _ in range(0, 6):
                try: 
                    message = await page2.wait_for('tr:has(span[name="UEFA"]) td:nth-child(5) span > span[data-thread-id]', timeout=20)
                    is_authenticated = True
                    break
                except: 
                    try:
                      refresh_button = await page2.select('div[data-tooltip="Refresh"]')
                      await refresh_button.mouse_click()
                    except: pass
            print(message.text)
            if not message: 
                print("Не вдалося отримати лист з кодом.")
                

            if "Here’s your confirmation code " in message.text:
                await message.mouse_click()



            code = False
            try:
                code = await page2.wait_for('table > tbody > tr > td > table > tbody > tr > td > div > table > tbody > tr > td > div:nth-child(3) > table > tbody > tr > td > table > tbody > tr:nth-child(3) > td > div', timeout=5)
            except: pass


            if code:
                await page2.close()
                await page.activate()
               
            else:
                print('page not activated')
                await page2.close()
                await page.activate()
                await page.reload()
                logger.info(f"Спроба {attempt + 1} перезавантажити сторінку")
                await page.evaluate('document.cookie.split(";").forEach(cookie => document.cookie = cookie.trim().replace(/=.*/, "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/"));')
                continue
            
            confirmation_input = False
            try: confirmation_input = await page.wait_for('#gigya-custom-pin-code-container > div > div', timeout=10)
            except Exception as e: print(e)
            confirmation_input = await page.select_all('#gigya-custom-pin-code-container > div > div > input')
            for index, input_el in enumerate(confirmation_input):
                await input_el.send_keys(code.text[index])
            
            continue_button = await page.select('#gigya-otp-update-form > div:nth-child(3) > div > input')
            await continue_button.mouse_click()
            time.sleep(5)

            # AFTER REGISTRATION COMPLETE
            close_popup = False
            try:
                close_popup = await page.wait_for('a[aria-label="close window"]', timeout=10)
                await close_popup.mouse_click()
            except: pass
            avatar_button = False
            try:
                avatar_button = await page.wait_for('pk-avatar[style="--pk-avatar--size: 24px;"]', timeout=10)
                await avatar_button.mouse_click()
            except: 
                await page.reload()
                logger.info(f"Спроба {attempt + 1} перезавантажити сторінку")
                await page.evaluate('document.cookie.split(";").forEach(cookie => document.cookie = cookie.trim().replace(/=.*/, "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/"));')
                continue
            time.sleep(2)
            first_name = await page.select('#gigya-textbox-firstName')
            await first_name.scroll_into_view()
            await first_name.send_keys(data['first_name'])
            last_name = await page.select('#gigya-textbox-lastName')
            await last_name.scroll_into_view()
            await last_name.send_keys(data['last_name'])

            dob_dd = await page.select('#gigya-textbox-96152432980421250')
            await dob_dd.scroll_into_view()
            await dob_dd.clear_input()
            await dob_dd.mouse_click()
            await dob_dd.send_keys(day)
            dob_mm = await page.select('#gigya-textbox-59935917301914800')
            await dob_mm.scroll_into_view()
            await dob_mm.clear_input()
            await dob_mm.mouse_click()
            await dob_mm.send_keys(month)
            dob_yyyy = await page.select('#gigya-textbox-145790993623807550')
            await dob_yyyy.scroll_into_view()
            await dob_yyyy.clear_input()
            await dob_yyyy.mouse_click()
            await dob_yyyy.send_keys(year)

            save_button = await page.select('#gigya-profile-form > div:nth-child(9) > div.gigya-composite-control.gigya-composite-control-submit > input')
            await save_button.scroll_into_view()
            await save_button.mouse_click()

            time.sleep(5)

            your_teams_button = await page.select('#idp-modal-wrapper > div > div > div.idp-myuefa-userprofile__left > div > nav > div:nth-child(2)')
            await your_teams_button.scroll_into_view()
            await your_teams_button.mouse_click()
            
        except Exception as e: 
            print("Error in main function", e)
        input('continue?')
        if isValid:
            break
        else:
            await page.reload()
            logger.info(f"Спроба {attempt + 1} перезавантажити сторінку")
    
    await page.close()
    ads_request(adspower_api if adspower_api else API_KEY, f'/api/v1/browser/stop?serial_number={data["serial_number"]}')
    isValid = isValid is not None
    return isValid


def switch_frame(browser, iframe) -> Tab:
    iframe: Tab = next(
        filter(
            lambda x: str(x.target.target_id) == str(iframe.frame_id), browser.targets
        )
    )
    iframe.websocket_url = iframe.websocket_url.replace("iframe", "page")
    return iframe


def run_test(data, adspower_api=None):
    active_browsers = []
    necessary_browsers = []
    for ads_user in data:
        serial_number = ads_user['serial_number']
        group_list = f'/api/v1/browser/active?serial_number={serial_number}'
        resp = ads_request(adspower_api if adspower_api else API_KEY, group_list)
        if resp['data']['status'] == 'Active':
            active_browsers.append(ads_user)
            continue
        else:
            necessary_browsers.append(ads_user)

    if active_browsers:
        for active_browser in active_browsers:
            logger.warning(f"Деякі браузери залишились увімкненими: {active_browser['email']}, {active_browser['serial_number']}")
        return {"status": False, "data": active_browsers}

    success_count, processed_count, problem_browsers = uc.loop().run_until_complete(process_browsers(necessary_browsers))

    if success_count == len(necessary_browsers):
        logger.log(SUCCESS, f"Кількість валідних браузерів: {success_count}/{len(necessary_browsers)}")
    else:
        logger.log(FAILURE, f"Кількість валідних браузерів: {success_count}/{len(necessary_browsers)}")

    logger.info(f"Кількість оброблених браузерів: {processed_count}/{len(necessary_browsers)}")
    
    data = {"status": True, "additional": problem_browsers, "data": success_count, "processed": necessary_browsers}
    return data


async def process_browsers(necessary_browsers, adspower_api=None):
    success_count, processed_count = 0, 0
    problem_browsers = []
    for necessary_browser in necessary_browsers:
        group_list = f'/api/v1/browser/start?serial_number={necessary_browser["serial_number"]}'
        for _ in range(0, 5):
            resp = ads_request(adspower_api if adspower_api else API_KEY, group_list)
            if resp: 
                break
        if not resp: 
            logger.error("В одному з браузерів сталася непередбачувана помилка")
            continue
        host, port = resp['data']['ws']['selenium'].split(':')
        if host and port:
            config = uc.Config(
                user_data_dir=None, headless=False, browser_executable_path=None,
                browser_args=None, sandbox=True, lang='en-US', host=host, port=int(port)
            )
            result = await main(config=config, data=necessary_browser, adspower_api=adspower_api)
            if result: 
                success_count += 1
                logger.log(INFO, f"Оброблено браузерів: {processed_count + 1}/{len(necessary_browsers)} | {necessary_browser['email']}")
            else: 
                logger.error(f"В одному з браузерів не вдалося створити аккаунт: {necessary_browser['email']}, {necessary_browser['serial_number']}")
                problem_browsers.append(f"В одному з браузерів не вдалося створити аккаунт: {necessary_browser['email']}, {necessary_browser['serial_number']}")
            processed_count += 1
    return success_count, processed_count, problem_browsers


def switch_frame(browser, iframe) -> Tab:
    iframe: Tab = next(
        filter(
            lambda x: str(x.target.target_id) == str(iframe.frame_id), browser.targets
        )
    )
    iframe.websocket_url = iframe.websocket_url.replace("iframe", "page")
    return iframe


if __name__ == "__main__":
    # link = input('link: ')
    link = 'https://docs.google.com/spreadsheets/d/12T5OaJ3f4KNnAQEt6JzQVJ5zWrkNCz8B5ufwPFghAfA/edit?gid=0#gid=0'
    # adspower_api = input('adspower api: ')
    adspower_api = 'http://local.adspower.net:50325'
    formatted_link = link.split('/')[5]
    # data = get_data_from_range(sheet="Work mail", start_col="B", end_col="C", spreadsheet_id=formatted_link)
    data = get_data_from_google_sheets(SHEET_RANGE="A2:R", SHEET_ID=formatted_link)
    # print("\nOLD DATA", data)
    # print("\nNEW DATA", data_new)
    ddata = get_data_from_sheet(data)
    # print(ddata)
    fdata = format_fdata(ddata)
    pprint(fdata)
    run_test(fdata, adspower_api)
