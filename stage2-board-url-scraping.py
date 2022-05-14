import json
import sqlite3
import sys
import time
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service as chrome_service
from selenium.webdriver.chrome.options import Options as chrome_options
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver

file_out_path = 'output_of_second_tool.json'

Separator_for_csv = "\t"
DATABASE_PATH = "database.db"

HOW_MANY_WINDOWS_DO_YOU_NEED = 2
# 1 window is already open when we open the browser
HOW_MANY_WINDOWS_DO_YOU_NEED = HOW_MANY_WINDOWS_DO_YOU_NEED-1

def initDriver(IS_HEADLESS=False) -> webdriver:
    options = chrome_options()
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.headless = IS_HEADLESS
    prefs = {
        "profile.managed_default_content_settings.images": 2
    }
    options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome(service=chrome_service(
        ChromeDriverManager().install()), options=options)


class window:
    all_links = {}
    board_url = None
    count_load_failt = 0

    def __init__(self, driver, window_handle):
        self.driver = driver
        self.window_name = window_handle

    def load_board_page(self, board_url):
        self.all_links = {}
        self.driver.switch_to.window(self.window_name)
        self.board_url = board_url
        self.driver.delete_all_cookies()
        try:
            self.driver.get(self.board_url)
            self.count_load_failt = 0
        except:
            self.count_load_failt += 1
            if(self.count_load_failt == 4):
                return
            else:
                self.load_board_page(board_url)
        self.driver.execute_script("document.body.style.zoom='50%'")
        self.driver.execute_script(
            "javascript:setInterval(function(){window.scrollBy(0, window.innerHeight);}, Math.floor(500));")
        # self.driver.execute_script(
        #     "javascript:setInterval(function(){window.scrollBy(window.innerHeight - 10, window.innerHeight);}, Math.floor(1000));")
        
        
    temp_length = -1
    count = 0

    def is_loaded_full_images(self):
        if(self.board_url == None):
            return True
        time.sleep(2/HOW_MANY_WINDOWS_DO_YOU_NEED)
        self.get_link_pin()
        end = self.driver.execute_script("let h2_tags = document.getElementsByTagName('h2');for (let index = 0; index < h2_tags.length; index++) {if(h2_tags[index].innerText == 'More like this'){return 1;break;}};return 0;")
        if(end):
            return True
        print(len(self.all_links), " pins.")
        if(self.temp_length == len(self.all_links)):
            self.count += 1
            if(self.count == 5):
                self.count = 0
                return True
        else:
            self.temp_length = len(self.all_links)
            self.count = 0
        return False

    def get_link_pin(self):
        self.driver.switch_to.window(self.window_name)
        try:
            mother_of_a_tag = self.driver.execute_script(
                "return document.getElementsByClassName('mobileGrid')[0]").get_attribute('innerHTML')
        except:
            return
        soup = BeautifulSoup(mother_of_a_tag, 'html.parser')
        for i in soup.find_all('a'):
            try:
                id = i['href']
            except:
                continue
            if(id.find("/pin/") != -1):
                self.all_links[id] = None
                self.push_to_database("https://www.pinterest.com"+id)

    def push_to_database(self, pin_url):
        cmd = "insert into stage2(board_url, pin_url) values ('" + \
            str(self.board_url)+"','"+str(pin_url)+"')"
        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                conn.execute(cmd)
                conn.commit()
        except Exception as e:
            if(str(e).lower().find("unique") != -1):
                pass
            elif(str(e).lower().find("database is locked") != -1):
                time.sleep(1)
                self.push_to_database(pin_url)
            else:
                print(str(e))


def process(board_list):
    driver = initDriver()
    try:
        driver.maximize_window()
    except:
        pass
    for i in range(HOW_MANY_WINDOWS_DO_YOU_NEED):
        driver.execute_script("window.open('');")
        
    windows = {}
    for i in driver.window_handles:
        windows[i] = window(driver, i)

    # process
    index = 0
    while(index < len(board_list)):
        for i in windows:
            if(windows[i].is_loaded_full_images()):
                board_url = "https://www.pinterest.com"+board_list[index]
                windows[i].load_board_page(board_url)
                set_board_is_scraped(board_url)
                index += 1
                print("Board line : ", index, "; url: ", board_url)

def output_json_file():
    json_data = []
    data = {}
    number_of_images = {}
    cmd = "select board_url, pin_url from stage2"
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.execute(cmd)
        conn.commit()
    cursor_temp = []
    for i in cursor:
        cursor_temp.append(i)
    cmd = "select board_url, pin_url, count(pin_url) from stage2 group by board_url"
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor_for_pins = conn.execute(cmd)
        conn.commit()
    for cur in cursor_for_pins:
        number_of_images[cur[0]] = cur[2]
    for cur in cursor_temp:
        data[cur[0]] = None
    
    count = 0
    for board_url in data:
        count+=1
        print("Writting ", count," -> ", board_url)
        pins = []
        for cur in cursor_temp:
            if(cur[0] == board_url):
                pins.append(cur[1])
        # print({"board url": board_url, "number of images": number_of_images[board_url], "pins": pins})
        json_data.append({"board url": board_url, "number of images": number_of_images[board_url], "pins": pins})
    json_data = {get_search_term():json_data}
    json_string = json.dumps(json_data)

    with open(file_out_path, 'w') as outfile:
        outfile.write(json_string)

def get_board_urls():
    returns = []
    cmd = "select board_url from stage1"
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.execute(cmd)
            conn.commit()
            for i in cursor:
                returns.append(i[0])
    except:
        time.sleep(1)
        return get_board_urls()
    return returns

def get_search_term():
    cmd = "select search_term from stage1 LIMIT 1;"
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.execute(cmd)
            conn.commit()
            for i in cursor:
                return i[0]
    except:
        time.sleep(1)
        return get_search_term()
def set_board_is_scraped(url):
    cmd = "update stage1 set scraped = 1 where board_url = '"+url+"';"
    try:
        with sqlite3.connect(DATABASE_PATH) as conn:
            conn.execute(cmd)
            conn.commit()
    except Exception as e:
        print(str(e))
        time.sleep(1)
        return set_board_is_scraped(url)

if __name__ == '__main__':
    try:
        for i in range(len(sys.argv)):
            if(sys.argv[i] == '-o'):
                file_out_path = sys.argv[i+1]
                break
    except:
        print("file_out_path is not set yet!")

    board_urls = get_board_urls()
    
    process(board_urls)

    output_json_file()
    