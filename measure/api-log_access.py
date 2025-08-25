import random, time, os, shutil, re, codecs, sys, commands, json, traceback, getopt, httplib, subprocess
#import random, time, os, shutil, re, codecs, sys, json, traceback, getopt, http.client, subprocess
import signal, psutil
import numpy as np
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import *
from selenium.webdriver.common.keys import Keys
from multiprocessing import Process as Task, Queue, Lock
import multiprocessing as mp
from pyvirtualdisplay import Display
from subprocess import call, PIPE, STDOUT
from urlparse import urlparse
import json
import fcntl
#from urllib.parse import urlparse
#import importlib
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


# This script do not need to destroy browser process between navigations
# This script can not capture browser event traces

reload(sys)
#importlib.reload(sys)
sys.setdefaultencoding('utf-8')
up = r'../'

os.environ["DISPLAY"] = ":0"

ROOT = os.path.dirname(os.path.realpath(__file__))
PROFILE_TEMPLATE_DIR = os.path.join(ROOT, './profile-template')
CHROME = os.path.join(ROOT, "../arcanum/chromium/src/out/arc/chrome")
# CHROME = os.path.join(ROOT, "../clean108/chrome")
ext_path = ''
ext_path = os.path.join(ROOT, ext_path)
overhead_path = '/data/backtrack/results_new/overhead.json'

class FunctionTimeoutException(Exception):
    pass

class NavigationStuckException(Exception):
    pass

class TooManyTasksDead(Exception):
    pass

def restart_all_tasks(log_f):
    time.sleep(1)

    status = 'Restarting [PARENT SCRIPT]...'
    current_time = getlocaltime()
    string = '%s\t%s\n' % (current_time, status)
    print(string)
    log_f.write(string)
    log_f.close()
    argv = sys.argv + ['&']

    os.execl('/usr/local/bin/python', '/usr/local/bin/python', *sys.argv)

# Garbage collection of terminated chrome processes
def gc_chrome_tmp_files(force=False):
    global log_f
    tmp_dir = '/tmp'
    num = 0
    for p in os.listdir(tmp_dir):
        path = os.path.join(tmp_dir, p)
        if os.path.isfile(path) and p.startswith('domac-browser'):
            flag = force
            if not force:
                try:
                    pid = int(p.split('-')[-1])
                except ValueError:
                    continue
                try:
                    os.kill(pid, 0)
                except OSError:
                    # The pid is not running
                    flag = True
            if flag:
                try:
                    os.remove(path)
                    num += 1
                except OSError as e:
                    pass
    status = 'GC [%d] files.' % (num)
    current_time = getlocaltime()
    string = '%s\t%s\n' % (current_time, status)
    log_f.write(string)

# This function tries to ensure that no extra zombie children stick around
def kill_child_processes(parent_pid=None, parent=None, timeout=3, sig=signal.SIGTERM, include_parent = True):
    global log_f
    #current_time = getlocaltime()
    if not parent and not parent_pid:
        return (None, None)
    try:
        if not parent and parent_pid:
            parent = psutil.Process(parent_pid)
    except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
        return (None, None)
    if parent.pid == os.getpid():
        include_parent = False
    children = parent.children(recursive=True)
    if include_parent:
        children.append(parent)
    for process in children:
        #msg = '%s\tKilling child process [%d] of [%d]...\n' % (current_time, process.pid, parent.pid)
        #if log_f:
            #log_f.write(msg)
        try:
            process.send_signal(sig)
        except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
            pass
    gone, alive = psutil.wait_procs(children, timeout=timeout, callback=None)
    if alive:
        for process in alive:
            try:
                process.kill() # SEND SIGKILL
            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                pass
        gone, alive = psutil.wait_procs(alive, timeout=timeout, callback=None)
    return (gone, alive)

def get_child_processes(parent_pid):
    try:
        parent = psutil.Process(parent_pid)
    except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
        return None
    children = parent.children(recursive=True)
    return children

def kill_processes_by_name(name):
    for process in psutil.process_iter():
        try:
            cmdline = ' '.join(process.cmdline())
            if name not in cmdline:
                continue
            #sys.stdout.flush()
            #pid = process.pid
            kill_child_processes(parent = process)
        except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
            pass

def create_browser(window_size="1024,768", binary_path=None, user_dir=None, env=None, ext=None, log_file=None, headless=None, download_dir=None, domain=None, rank=None, instance_id=None):
    global domain2prefix
    print "now in create_browser, user_dir: "+user_dir+", domain: "+domain
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')   # for virtual display
    options.add_argument('--disable-component-extensions-with-background-pages')
    options.add_argument('--proxy-server=127.0.0.1:7895')
    options.add_argument("--disable-notifications")
    #options.add_argument("--remote-debugging-port=9222")
    options.add_argument('--window-size=%s' % window_size)

    # added on 2025/05/02
    options.add_argument("--no-default-browser-check")
    options.add_argument("--no-first-run")
    options.add_argument("--disk-cache-dir=/dev/null")
    options.add_argument("--disk-cache-size=0")
    options.add_argument("--memory-pressure-heuristic-period-ms=0")
    options.add_argument("--media-cache-size=0")
    options.add_argument("--disable-gpu")
    options.add_argument("--dns-prefetch-disable")

    prefix = domain2prefix[(rank,domain)]
    print rank,domain,prefix,instance_id

    options.add_argument('--js-flags=--cookie_script=x --accessing_domain='+domain+' --cookie_prefix='+prefix+' --instance_id='+str(instance_id))

    options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False
    })

    if binary_path:
        options.binary_location= binary_path
    if headless:
        options.add_argument('--headless')
    if user_dir:
        options.add_argument('--user-data-dir='+user_dir)
    if ext:
        if type(ext) == list:
            for e in ext:
                options.add_extension(os.path.join(ext_path, e))
        else:
            options.add_extension(os.path.join(ext_path, ext))

    #display = None
    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'performance': 'ALL'}

    display = Display(visible=0, size=(1024, 768))  
    #display = Display()  
    display.start()
    chromedriver_path = '/data/backtrack/new_selenium/v108-chromedriver'

    try:
        if log_file:
            browser = webdriver.Chrome(executable_path=chromedriver_path, chrome_options=options, desired_capabilities=caps, service_args=['--verbose', '--log-path=%s' % log_file])
        else:
            browser = webdriver.Chrome(executable_path=chromedriver_path, chrome_options=options, service=service, desired_capabilities=caps)
    except WebDriverException as e:
        print(e)
        print('Failed to create browser for PID [%d]!!!' % (os.getpid()))
        return (None, None)
    return (browser, display)

def close_browser(browser):
    browser.quit()

def wait_find_element_by_id(driver, _id, timeout=5):
    result = None
    try:
        result = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, _id)))
    except TimeoutException as e:
        pass
    return result

def wait_find_element_by_tag_name(driver, name, timeout=5):
    result = None
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, name)))
    except TimeoutException as e:
        pass
    return result

def wait_find_elements_by_tag_name(driver, name, timeout=5):
    result = None
    try:
        result = WebDriverWait(driver, timeout).until(EC.presence_of_all_element_located((By.TAG_NAME, name)))
    except TimeoutException as e:
        pass
    return result

def wait_find_element_by_class_name(driver, name, timeout=5):
    result = None
    try:
        result = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CLASS_NAME, name)))
    except TimeoutException as e:
        pass
    return result

def wait_find_elements_by_class_name(driver, name, timeout=5):
    result = None
    try:
        result = WebDriverWait(driver, timeout).until(EC.presence_of_all_element_located((By.CLASS_NAME, name)))
    except TimeoutException as e:
        pass
    return result

def wait_find_element_by_xpath(driver, xpath, timeout=5):
    result = None
    try:
        result = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
    except TimeoutException as e:
        pass
    return result

def wait_find_elements_by_xpath(driver, xpath, timeout=5):
    result = None
    try:
        result = WebDriverWait(driver, timeout).until(EC.presence_of_all_element_located((By.XPATH, xpath)))
    except TimeoutException as e:
        pass
    return result

def get_date_string(t):
    return time.strftime("%Y%m%d%H%M%S", t)

def get_time(t):
    return time.strftime("%Y-%m-%d %H:%M:%S", t)

def prepare_profile(user_dir, remove_only=False):
    try:
        shutil.rmtree(user_dir)
    except OSError as e:
        pass
    if not remove_only:
        shutil.copytree(PROFILE_TEMPLATE_DIR, user_dir)


def getlocaltime():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())



def save_result_files(logs_dir, rank, user_dir, first_party_url):
    global chrome_newtab_url, about_blank_url, chrome_extension_prefix, chrome_extension_suffix, last_rank, last_logs_dir, extract
    chrome_newtab_url = 'https://www.google.com/_/chrome/newtab'
    about_blank_url = 'about:blank'
    chrome_extension_prefix = 'chrome-extension://'
    chrome_extension_suffix = 'generated_background_page.html'


    last_rank = rank
    last_logs_dir = logs_dir
    subframe_count = 0
    substore_count = 0
    children_tmp1 = get_child_processes(os.getpid())
    dst_folder_tmp = logs_dir
    main_frame_pid = -1
    main_frame_filename = None

    found_mv_files = False
    for child in children_tmp1:
        try:
            child_pid = child.pid
        except Exception as e:
            child_pid = child
        mv_filename = str(child_pid) + '.frame'
        store_filename = str(child_pid) + '.store'
        is_main_frame_file = False
        try:
            f = open(mv_filename, 'r')
        except Exception as e:
            store_new_filename = str(rank) + '.' + 'sub.' + str(substore_count) + '.store'
            store_new_filename = os.path.join(dst_folder_tmp, store_new_filename)

            substore_count += 1
            try:
                shutil.move(store_filename, store_new_filename)
                found_mv_files = True
            except OSError as e:
                pass
            except IOError:
                pass
            continue

        try:
            lines = f.read().split('\n')[:-1]
            for line in lines:
                type_ = line.split(' ')[0]
                url_ = line.split(' ')[1]
                if(type_ == '[main]' and chrome_newtab_url not in url_ and about_blank_url not in url_):
                    if not (url_.startswith(chrome_extension_prefix) and url_.endswith(chrome_extension_suffix)):
                        i = 0
                        while True:
                            new_file = "%d.main.%d" %(rank, i)
                            mv_new_filename = new_file + ".frame"
                            mv_new_filename = os.path.join(dst_folder_tmp, mv_new_filename)
                            if not os.path.isfile(mv_new_filename):
                                store_new_filename = new_file + ".store"
                                store_new_filename = os.path.join(dst_folder_tmp, store_new_filename)
                                break
                            i += 1
                        is_main_frame_file = True
                        main_frame_pid = child_pid
                        main_frame_filename = mv_new_filename
                        break
            f.close()
            if not is_main_frame_file:
                mv_new_filename = str(rank) + '.' + 'sub.' + str(subframe_count) + '.frame'
                mv_new_filename = os.path.join(dst_folder_tmp, mv_new_filename)
                store_new_filename = str(rank) + '.' + 'sub.' + str(substore_count) + '.store'
                store_new_filename = os.path.join(dst_folder_tmp, store_new_filename)

                subframe_count += 1
                substore_count += 1
        except OSError as e:
            pass

        try:
            shutil.move(mv_filename, mv_new_filename)
            found_mv_files = True
        except OSError as e:
            pass
        except IOError:
            pass

        try:
            shutil.move(store_filename, store_new_filename)
            found_mv_files = True
        except OSError as e:
            pass
        except IOError:
            pass


def measure(user_dir, task_id, length, start, end, status_queue, process_index):
    global rank2domain, access_control, find_sub_pages_script, num_instances, log_dir, exp_dir,domain2prefix
    current_pid = os.getpid()
    random.seed(time.time())

    chrome_newtab_url = 'https://www.google.com/_/chrome/newtab'
    about_blank_url = 'about:blank'
    try:
        status = 'Process %-4d task %d/%d PID [%d] starting ...' % (process_index, task_id+1, length, current_pid)
        status_queue.put([process_index, status])
    except Exception as e:
        pass

    try:
        os.mkdir(user_dir)
    except OSError as e:
        pass
    os.chdir(user_dir)


    try:
        filenames = os.listdir(log_dir)
    except OSError as e:
        return
    logs_dir = user_dir+'_logs'
    logs_dir = os.path.join(log_dir, logs_dir)
    try:
        os.mkdir(logs_dir)
    except OSError as e:
        pass
    log_file = '%s.log' % (user_dir)
    log_file = os.path.join(log_dir, log_file)
    webdriver_log = 'webdriver_%s.log' % (user_dir)
    processed_list = list()
    failed_list = list()
    log_f = None
    # print "log_file:", {log_file}
    try:
        log_f = open(log_file, 'r')
        for line in log_f:
            data = line[:-1].split('\t')
            rank = int(data[1])
            status = data[3]
            if status == 'main':
                url = data[2]
                if not url.startswith(about_blank_url):
                    # print "add ",rank," to processed_list"
                    processed_list.append(rank)
            elif status == 'failed':
                url = data[2]
                if not url.startswith(about_blank_url):
                    failed_list.append(rank)
        log_f.close()
    except IOError as e:
        pass

    network_logged_domains = set()
    network_files = os.listdir(os.getcwd())
    network_files = [f for f in network_files if f.endswith('.network')]
    for f in network_files:
        d = f.split('.network')[0]
        network_logged_domains.add(d)

    filenames = [f for f in filenames if f.endswith('.json') and f.startswith(user_dir)]
    rank2files = dict()
    files = list()
    for i, json_file in enumerate(filenames):
        json_file = os.path.join(log_dir, json_file)
        input_f = open(json_file, 'r')
        files += json.loads(input_f.read())
        input_f.close()
    for f in files:
        rank, suffix = f.split('.')
        rank = rank.split('-')[0]
        try:
            rank = int(rank)
        except ValueError:
            continue
        if rank not in rank2files:
            rank2files[rank] = list()
        if suffix in ['api', 'network']: 
            rank2files[rank].append(suffix)
    completed_list = [rank for rank, suffix_list in rank2files.items() if len(suffix_list) >= 2]
    rank2files = dict()
    files = []
    try:
        files += os.listdir(logs_dir)
    except OSError as e:
        return
    files = [f for f in files if f.endswith('.api') or f.endswith('.network')] 
    for f in files:
        f_split_list = f.split('.')
        rank = f_split_list[0]
        try:
            rank = int(rank)
        except ValueError:
            continue
        if len(f_split_list) == 4:
            suffix = f_split_list[3]
        elif len(f_split_list) == 2:
            suffix = f_split_list[1]
        if rank not in rank2files:
            rank2files[rank] = list()
        if suffix in ['api', 'network']:
            rank2files[rank].append(suffix)
    completed_list += [rank for rank, suffix_list in rank2files.items() if len(suffix_list) >= 2]
    del rank2files

    browser = None
    chromedriver_process = None
    display = None
    count = 0
    task_list = set(processed_list + failed_list)
    task_list = set([rank for rank in task_list if rank >= start and rank <= end])
    processed_list = set(completed_list + failed_list)
    processed_list = set([rank for rank in processed_list if rank >= start and rank <= end])

    rank2fail_num = dict()
    # print("rank2domain, ", rank2domain)
    while True:
        try:
            last_url = None
            # print "going to for"
            for rank, domain in sorted(rank2domain.items()):
                # print("processed_list, ", processed_list)
                # print process_index, "target domain: ", domain
                # print(rank, task_id, rank % num_instances)
                if rank > end:
                    # print('2')
                    break
                if rank % num_instances != task_id or rank in processed_list or rank < start:
                    # print(rank % num_instances)
                    # print(task_id)
                    # print(rank % num_instances != task_id, rank in processed_list, rank<start)
                    continue
                if rank in rank2fail_num and rank2fail_num[rank] >= 3:
                    # print('3')
                    continue
                task_list.add(rank)
                # print('pass filter')
                if browser is None or count % 1 == 0:
                    if browser is not None:
                        try:
                            close_browser(browser)
                        except Exception as e:
                            pass
                        except KeyboardInterrupt as e:
                            raise
                    if display is not None:
                        try:
                            display.stop()
                        except Exception as e:
                            pass
                    gone, alive = kill_child_processes(parent_pid = current_pid)
                    process_name = 'user-data-dir=%s' % (user_dir)
                    kill_processes_by_name(process_name)
                    process_name = 'log-path=webdriver_%s.log' % (user_dir)
                    kill_processes_by_name(process_name)

                    i = 0
                    download_dir = logs_dir
                    instance_id = random.randint(1000,9999)
                    while True:
                        prepare_profile(user_dir=user_dir)
                        # Register the signal function handler
                        signal.signal(signal.SIGALRM, function_timeout_handler)
                        # Define a timeout for the function
                        timeout = min(max(i, 15), 30)
                        signal.alarm(timeout)
                        # Run the function
                        try:
                            # print("goto create_browser")
                            browser, display = create_browser(binary_path=CHROME, user_dir = user_dir, env=access_control, log_file=webdriver_log, headless=False, download_dir=download_dir, domain=domain, rank=rank, instance_id=instance_id)
                            # print "created, url: " + browser.current_url
                            if browser is not None:
                                chromedriver_process = browser.service.process
                        except (FunctionTimeoutException, OSError) as e:
                            print(e)
                            status = 'Process %-4d task %d/%d browser creation failed!!!' % (process_index, task_id+1, length)
                            status_queue.put([process_index, status])
                            string = '%s\t%s' % (getlocaltime(), status)
                            browser = None
                        except (KeyboardInterrupt, Exception) as e:
                            signal.alarm(0)
                            raise e
                        # Cancel the timer if the function returned before timeout
                        #print('finished creating browser', browser)
                        signal.alarm(0)
                        if browser is not None:
                            time.sleep(1)
                            break
                        gone, alive = kill_child_processes(parent_pid = current_pid)
                        process_name = 'user-data-dir=%s' % (user_dir)
                        kill_processes_by_name(process_name)
                        process_name = 'log-path=webdriver_%s.log' % (user_dir)
                        kill_processes_by_name(process_name)

                        i += 1
                        low = 1
                        high = 5
                        sleep_interval = random.randint(low, high)
                        time.sleep(sleep_interval)

                time.sleep(2)
                # Register the signal function handler
                signal.signal(signal.SIGALRM, function_timeout_handler)
                # Define a timeout for the function
                timeout = 700
                signal.alarm(timeout)
                start_time = time.time()
                # Run the function

                #try: # except FunctionTimeoutException as e:
                if input_type == 'url':
                    url = domain
                else:
                    url = "http://www."+domain

                opened_handles = set(browser.window_handles)
                while len(opened_handles) > 1:
                    new_handle = opened_handles.pop()
                    browser.switch_to_window(new_handle)
                    try:
                        alert1 = browser.switch_to_alert()
                        alert1.dismiss()
                    except Exception as e:
                        pass
                    try:
                        browser.close()
                    except NoSuchWindowException as e:
                        pass
                try:
                    opened_handles = set(browser.window_handles)
                    new_handle = opened_handles.pop()
                    browser.switch_to_window(new_handle)
                except KeyError:
                    pass

                try:
                    browser.set_page_load_timeout(600)
                    time.sleep(5)
                    print "Process", process_index, "going to access", url
                    start_ts = time.time()
                    browser.get(url)
                    status = 'Process %-4d task %d/%d %s loaded in %f seconds' % (process_index, task_id+1, length, url, time.time() - start_time - 5)
                    record = {
                        "domain": domain,
                        "cookiehead":domain2prefix[(rank,domain)],
                        "instance_id":instance_id,
                        "start_ts":start_ts,
                        "loadtime": time.time() - start_ts
                    }
                    # with open(overhead_path, 'a+') as f:
                    #     f.seek(0)
                    #     try:
                    #         data = json.load(f)
                    #         if not isinstance(data, list):
                    #             data = []
                    #     except (ValueError, IOError):
                    #         data = []
                    #     data.append(record)
                    #     f.seek(0)
                    #     f.truncate()
                    #     json.dump(data, f, indent=2)
                    #     f.write('\n')
                    with open(overhead_path, 'a+') as f:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                        try:
                            f.seek(0, os.SEEK_END)
                            f.write(json.dumps(record, ensure_ascii=False))
                            f.write('\n')
                            f.flush()
                            os.fsync(f.fileno())
                        finally:
                            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

                except TimeoutException as e:
                    status = 'Process %-4d task %d/%d %s timed out in %f seconds' % (process_index, task_id+1, length, url, time.time() - start_time - 5)
                    #sys.stdout.flush()
                    pass
                except UnexpectedAlertPresentException as e:
                    alert1 = browser.switch_to_alert()
                    #browser.switch_to_window(current_handle)
                    #browser.switch_to_window(current_handle)
                    alert1.dismiss()
                except Exception as e:
                    print "exception during get url %s:" % (domain), e
                    pass

                print status

                try:
                    # Wait for at most another 30 seconds if the get(url) call above has timed out
                    time.sleep(1)
                    # print "here"
                    # WebDriverWait(browser, 20).until(lambda d: d.execute_script('return document.readyState;') == 'complete')
                    # print "hhh"
                    sys.stdout.flush()
                    status = 'Process %-4d task %d/%d %s waited in %f seconds' % (process_index, task_id+1, length, url, time.time() - start_time)
                    print(status)
                    # state = browser.execute_script("return document.readyState")
                    # print(state)
                    #sys.stdout.flush()
                except TimeoutException as e:
                    # This is the second TimeoutException, we need to abort the page load
                    # print "here1"
                    status = 'Process %-4d task %d/%d %s timed out again in %f seconds' % (process_index, task_id+1, length, url, time.time() - start_time)
                    #print(status)
                    #sys.stdout.flush()
                    # We wait for at most another 30 seconds to stop the page load
                    browser.set_page_load_timeout(5)
                    try:
                        webdriver.ActionChains(browser).send_keys(Keys.ESCAPE).perform()
                    except TimeoutException as e:
                        # This is the third TimeoutException. Try to abort the page load one more time
                        # If we cannot stop it in another 5 seconds, a TimeoutException will be caught finally
                        browser.execute_script("window.stop();") # We have to use JavsScript to stop page loading
                except UnexpectedAlertPresentException as e:
                    # print "here3"
                    sys.stdout.flush()
                    alert1 = browser.switch_to_alert()
                    #browser.switch_to_window(current_handle)
                    #browser.switch_to_window(current_handle)
                    alert1.dismiss()
                except WebDriverException as e:
                    print("Selenium WebDriver error: ", e)
                    sys.stdout.flush()
                except Exception as e:
                    print "exception during waiting readyState:",e
                    sys.stdout.flush()
                finally:
                    # print("here22"); sys.stdout.flush()
                    pass

                # We wait for at most 10 second for reading the current_url
                # print "here2"
                
                current_url = None
                try:
                    browser.set_page_load_timeout(10)
                    current_url = browser.current_url
                    print "current url: " + current_url
                except TimeoutException as e:
                    # We need to abort the page load
                    try:
                        browser.set_page_load_timeout(5)
                        # print "23"
                        webdriver.ActionChains(browser).send_keys(Keys.ESCAPE).perform()
                        current_url = browser.current_url
                    except TimeoutException as e:
                        # This is the second TimeoutException. Try to abort the page load one more time
                        # If we cannot stop it in another 5 seconds, a TimeoutException will be caught finally
                        # print "11"
                        try:
                            browser.execute_script("window.stop();") # We have to use JavsScript to stop page loading
                        except Exception as e:
                            pass
                except Exception as e:
                    pass
                if current_url:
                    # print "d"
                    url = current_url
                if url == last_url or url.startswith(chrome_newtab_url) or url.startswith(about_blank_url):
                    # print "ds"
                    raise NavigationStuckException("Url is identical with url of last navigation!")
                # print "ss"

                # save_result_files(logs_dir, rank, user_dir, url)

                # request_file = '%d.network'%(rank) #domain.split('\r')[0])
                # browser_log = browser.get_log('performance')
                # with open(request_file, 'w') as output_f:
                #     for entry in browser_log:
                #         response = json.loads(entry['message'])['message']
                #         if 'Network.requestWillBeSent' in response['method']:
                #             output_f.write('[request]'+json.dumps(response)+'\n')
                #         elif 'Network.responseReceived' in response['method']:
                #             output_f.write('[response]'+json.dumps(response)+'\n')

                count = 0
                while count < 3:
                    count += 1
                    try:
                        alert1 = browser.switch_to_alert()
                        #alert1.accept()
                        alert1.dismiss()
                    except Exception as e:
                        pass

                # tcf_api_result = browser.execute_script("__tcfapi('getTCData', 2, (data, success) => {if(success) {apiRes=JSON.stringify(data);}else { apiRes='null';}}); return apiRes;")
                # try:
                #     tcf_api_result = json.dumps(tcf_api_result)
                # except Exception as e:
                #     pass
                # with open('%d.api'%(rank), 'w') as output_f:
                #     output_f.write(tcf_api_result)

                # src_logs_filename = os.path.join(os.getcwd(), '%d.api'%(rank))
                # dst_logs_filename = os.path.join(logs_dir, '%d.api'%(rank))
                # try:
                #     shutil.move(src_logs_filename, dst_logs_filename)
                # except IOError as e:
                #     pass
                # except OSError as e:
                #     pass
                # src_logs_filename = os.path.join(os.getcwd(), '%d.network'%(rank))
                # dst_logs_filename = os.path.join(logs_dir, '%d.network'%(rank))
                # try:
                #     shutil.move(src_logs_filename, dst_logs_filename)
                # except IOError as e:
                #     pass
                # except OSError as e:
                #     pass


                count = 0
                while count < 3:
                    count += 1
                    try:
                        alert1 = browser.switch_to_alert()
                        #alert1.accept()
                        alert1.dismiss()
                    except Exception as e:
                        pass
                try:
                    browser.set_window_size(1024, 768)
                except Exception as e:
                    pass
                log_f = open(log_file, 'a')
                status = 'main'
                l = '%s\t%d\t%s\t%s\n' % (getlocaltime(), rank, url, status)
                log_f.write(l)
                log_f.close()

                last_url = url

                status = 'Process %-4d task %d/%d %s [%d] loaded.' % (process_index, task_id+1, length, url, rank)
                status_queue.put([process_index, status])

                processed_list.add(rank)
                count += 1

                # Cancel the timer if the function returned before timeout
                signal.alarm(0)

            remaining_tasks = task_list - processed_list
            if len(remaining_tasks) == 0:
                break
        except KeyboardInterrupt as e:
            #kill_child_processes(parent_pid = current_pid)
            kill_all_processes()
            pass
        except Exception as e:
        #except (KeyboardInterrupt, Exception) as e:
            signal.alarm(0)
            if log_f:
                log_f.close()
            status = 'Process %-4d task %s/%s raised an exception %s when visiting [%d].' % (process_index, task_id+1, length, type(e), rank)
            status_queue.put([process_index, status])
            string = '%s\t%s' % (getlocaltime(), status)
            if not isinstance(e, WebDriverException) and not isinstance(e, TimeoutException) and not isinstance(e, httplib.CannotSendRequest) and not isinstance(e, FunctionTimeoutException) and not isinstance(e, NavigationStuckException) and not isinstance(e, httplib.BadStatusLine):
            #if not isinstance(e, TimeoutException) and not isinstance(e, httplib.CannotSendRequest) and not isinstance(e, FunctionTimeoutException) and not isinstance(e, NavigationStuckException) and not isinstance(e, httplib.BadStatusLine):
                try:
                    print(string)
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                    print(''.join('!! ' + line for line in lines))
                    sys.stdout.flush()
                except Exception:
                    pass
            if isinstance(e, IOError):
                kill_all_processes()
            if rank not in rank2fail_num:
                rank2fail_num[rank] = 1
            else:
                if isinstance(e, WebDriverException):
                    rank2fail_num[rank] += 0.5
                else:
                    rank2fail_num[rank] += 1
            print rank2fail_num[rank], "times"
            print e,"error"
            if rank2fail_num[rank] >= 3:
                # We need to add the failed rank to processed_list.
                # Otherwise, the While loop won't terminate
                processed_list.add(rank)
                log_f = open(log_file, 'a')
                status = 'failed'
                l = '%s\t%d\t%s\t%s\n' % (getlocaltime(), rank, domain, status)
                log_f.write(l)
                log_f.close()
                status = 'Process %-4d task %s/%s failed to visit [%d] %s.' % (process_index, task_id+1, length, rank, domain)
                status_queue.put([process_index, status])
                record = {
                    "domain":domain,
                    "cookiehead":domain2prefix[(rank,domain)],
                    "loadtime":-1
                }
                # with open(overhead_path, 'a+') as f:
                #     f.seek(0)  # move to file head
                #     try:
                #         data = json.load(f)
                #         if not isinstance(data, list):
                #             data = []
                #     except (ValueError, IOError):
                #         # file empty or non-json format, init it
                #         data = []
                #     data.append(record)
                #     f.seek(0)
                #     f.truncate()
                #     json.dump(data, f, indent=2)
                #     f.write('\n')
                with open(overhead_path, 'a+') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        f.seek(0, os.SEEK_END)
                        f.write(json.dumps(record, ensure_ascii=False))
                        f.write('\n')
                        f.flush()
                        os.fsync(f.fileno())
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            if browser is not None:
                close_browser(browser)
            if display is not None:
                try:
                    display.stop()
                except Exception as e:
                    pass

            browser = None
    try:
        if browser is not None:
            close_browser(browser)
        if display is not None:
            try:
                display.stop()
            except Exception as e:
                pass

        gone, alive = kill_child_processes(parent_pid = current_pid)
        process_name = 'user-data-dir=%s' % (user_dir)
        kill_processes_by_name(process_name)
        process_name = 'log-path=webdriver_%s.log' % (user_dir)
        kill_processes_by_name(process_name)
    except (KeyboardInterrupt, Exception) as e:
        if not isinstance(e, KeyboardInterrupt):
            print(e)
    status = 'Process %-4d task %s/%s PID [%d] completed.' % (process_index, task_id+1, length, current_pid)
    status_queue.put([process_index, status])
    #print(status)
    prepare_profile(user_dir=user_dir, remove_only=True)

def function_timeout_handler(sig, frame):
    raise FunctionTimeoutException("Function Timeouted!")

def signal_term_handler(sig, frame):
    global parent_pid
    current_pid = os.getpid()
    if current_pid == parent_pid:
        #msg = '%s\tPARENT PROCESS [%d] received SIGTERM!!! Killing all child processes...\n' % (current_time, current_pid)
        process_name = 'chrome'
        kill_processes_by_name(process_name)
    kill_all_processes()

def kill_all_processes(restart_parent_flag=False):
    global parent_pid, process_list, log_f
    current_time = getlocaltime()
    current_pid = os.getpid()
    if current_pid == parent_pid:
        msg = '%s\tPARENT PROCESS [%d] received SIGTERM!!! Killing all child processes...\n' % (current_time, current_pid)
    else:
        msg = '%s\tProcess [%d] received SIGTERM!!! Killing all child processes... PARENT PID=[%d]\n' % (current_time, current_pid, parent_pid)
    #print(msg)
    #sys.stdout.flush()
    log_f.write(msg)
    kill_child_processes(parent_pid = current_pid)
    current_time = getlocaltime()
    msg = '%s\tAll child processes of Process [%d] are killed!!!\n' % (current_time, current_pid)
    #print(msg)
    log_f.write(msg)
    if current_pid == parent_pid:
        if restart_parent_flag:
            restart_all_tasks(log_f)
        else:
            log_f.close()
    sys.exit()

def main(argv):
    global rank2domain, input_type, access_control, num_instances, parent_pid, process_list, log_f, log_dir, exp_dir, domain2prefix
    signal.signal(signal.SIGTERM, signal_term_handler)
    start_time = time.time()
    try:
        opts, args = getopt.getopt(argv, 'hu:d:i:n:p:t:s:e:', ['help', 'user_dir=', 'log_dir=', 'num=', 'process=', 'type=', 'input_file=', 'start=', 'end='])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    user_dir = None
    access_control = True
    input_type = 'domain'
    input_file = 'top-1m.csv'
    num_instances = 512
    maximum_process_num = 8 # Change to 1 for debugging purpose
    start = 0
    end = None
    exp_dir = "exps"
    log_dir = ""
    for opt, arg in opts:
        if opt in ('-u', '--user_dir'):
            user_dir = arg
        elif opt in ('-d', '--dir'):
            log_dir = arg
        elif opt in ('-i', '--input_file'):
            input_file = arg
        elif opt in ('-n', '--num'):
            num_instances = int(arg)
        elif opt in ('-p', '--process'):
            maximum_process_num = int(arg)
        elif opt in ('-t', '--type'):
            input_type = arg
        elif opt in ('-s', '--start'):
            start = int(arg)
        elif opt in ('-e', '--end'):
            end = int(arg)
        elif opt in ('-h', '--help'):
            usage()
            sys.exit(0)
    if user_dir is None:
        usage()
        sys.exit(0)


    try:
        os.mkdir(exp_dir)
    except OSError as e:
        pass
    try:
        os.mkdir(log_dir)
    except OSError as e:
        pass

    parent_pid = os.getpid()
    script_dir = os.getcwd()
    restart_parent_flag = False

    log_file = 'exp_%s.log' % (user_dir)
    log_file = os.path.join(log_dir, log_file)
    log_f = codecs.open(log_file, encoding='utf-8', mode='a')
    current_time = getlocaltime()
    status = "PARENT SCRIPT STARTED! PARENT PID=[%d]" % parent_pid
    string = '%s\t%s\n' % (current_time, status)
    print(string)
    log_f.write(string)
    string = "%s\tProcess started, argv=%s\n" % (current_time, argv)
    log_f.write(string)

    completed_list = set()
    completion_reg = re.compile('Process [0-9\s]+task ([0-9]+)/[0-9]+ PID \[\d+\] completed.')
    with codecs.open(log_file, encoding='utf-8', mode='r') as input_f:
        for line in input_f:
            match = re.search(completion_reg, line)
            if match:
                task = int(match.group(1)) - 1
                completed_list.add(task)
    completed_list = set()

    input_f = open(input_file, 'r')
    lines = input_f.read().split('\n')[:-1]
    input_f.close()
    rank2domain = dict()
    domain2prefix = dict()
    for line in lines:
        # data = line.split(',')
        # rank = data[0]
        # rank = int(rank)
        # url = ','.join(data[1:])
        # rank2domain[rank] = url
        parts = line.rstrip("\n").split(",", 2)
        rank_str, domain = parts[0], parts[1]
        prefix = parts[2] if len(parts) > 2 else None

        rank = int(rank_str)
        rank2domain[rank] = domain

        if prefix is not None:
            domain2prefix[(rank,domain)] = prefix


    if end is None:
        end = len(rank2domain)
    # print("rank2domain_init: " ,rank2domain)
    # print("domain2prefix_init: " ,domain2prefix)



    try:
        os.chdir(exp_dir)
    except OSError as e:
        pass

    # Remove temp files
    gc_chrome_tmp_files(force=True)

    process_name = 'chrome'
    kill_processes_by_name(process_name)

    tasks = [i for i in range(num_instances-1, -1, -1)]
    status_queue = Queue()
    try:
        length = len(tasks)
        head = 'Preparing [%d] task ...' % (length)
        final_status_set = set()
        progress = dict()
        for j in range(maximum_process_num, 0, -1):
            progress[j] = ''
        id_pool = [j for j in range(maximum_process_num, 0, -1)]
        process_num = 0
        process2status = dict()
        running_processes = set()
        process2id = dict()
        process2index = dict()
        process2start_time = dict()
        id2index = dict()
        id2task = dict()
        index2task = dict()
        round_num = 0
        process_list = list()
        killed_process_list = list()
        dead_num = 0
        dead_ratio = 0
        alive_check_timeout = 60
        dead_ratio_list = []
        alive_count = 0

        while len(tasks) > 0 or len(running_processes) > 0: 
            current_time = getlocaltime()
            num_alive_processes = sum(1 for process in process_list if process.is_alive())
            status = '[%d] processes are still alive, [%d] are running ...' % (num_alive_processes, len(running_processes))
            string = '%s\t%s\n' % (current_time, status)
            print(string)
            sys.stdout.flush()
            # print("tasks: ", tasks)

            while len(running_processes) < maximum_process_num and len(tasks) > 0:
                group = tasks.pop()
                task = group
                if task in completed_list:
                    continue
                user_dir_group = '%s_%d' % (user_dir, group)
                process_index = process_num
                try:
                    print("going to create process")
                    process_list.append(Task(target=measure, args=(user_dir_group, task, length, start, end, status_queue, process_index)))
                    process = process_list[-1]
                    process.start()
                except OSError as e:
                    print("subprocess start error, ", e)
                    tasks.append(group)
                    time.sleep(5)
                    continue
                process_num += 1
                running_processes.add(process)
                process2index[process] = process_index
                process2start_time[process] = time.time()
                index2task[process_index] = task

                current_time = getlocaltime()
                process_status = 'Process %-4d task %d/%d created. PID=%d ...' % (process_index, task+1, length, process.pid)
                string = '%s\t%s' % (current_time, process_status)
                print(string)
                sys.stdout.flush()
                if process_num % 20 == 0:
                    break

            #time.sleep(1)
            flag = False
            # print("goto while? ",any(process.is_alive() for process in process_list))
            while any(process.is_alive() for process in process_list):
                time.sleep(1)
                current_time = getlocaltime()
                alive_count += 1
                num_alive_processes = sum(1 for process in process_list if process.is_alive())

                #flag = False
                while not status_queue.empty():
                    process_index, process_status = status_queue.get()
                    string = '%s\t%s\n' % (current_time, process_status)
                    log_f.write(string)
                    if 'completed' in process_status:
                        flag = True
                        if process_status not in final_status_set:
                            final_status_set.add(process_status)

                if alive_count % alive_check_timeout == 0:
                    status = '[%d] processes are still alive ...' % (num_alive_processes)
                    string = '%s\t%s\n' % (current_time, status)
                    print(string)
                    sys.stdout.flush()

                    gc_chrome_tmp_files()
                    current_timestamp = time.time()
                    elapse = current_timestamp - start_time
                    dead_num = 0
                    # We need to get a list. Otherwise, we will receive an exception: RuntimeError: Set changed size during iteration
                    for process in list(running_processes):
                        process_index = process2index[process]
                        group = index2task[process_index]

                        if not process.is_alive():
                            flag = True
                            process_status = 'Process %-4d task %d/%d is no longer alive...' % (process_index, group+1, length)
                        else:
                            process_status = 'Process %-4d task %d/%d is still alive...' % (process_index, group+1, length)
                        string = '%s\t%s\n' % (current_time, process_status)
                        log_f.write(string)

                        # Start checking log file modification time after 10 minutes
                        if elapse >= 60*10:
                            process_start_time = process2start_time[process]
                            process_elapse = current_timestamp - process_start_time
                            user_dir_group = '%s_%d' % (user_dir, group)
                            user_dir_log_file = '%s.log' % (user_dir_group)
                            user_dir_log_file = os.path.join(log_dir, user_dir_log_file)
                            #mtime = current_timestamp
                            ctime = current_timestamp
                            try:
                                #mtime = os.path.getmtime(user_dir_log_file) # https://docs.python.org/2/library/os.path.html#os.path.getmtime
                                ctime = os.path.getctime(user_dir_log_file) # https://docs.python.org/2/library/os.path.html#os.path.getctime
                            except OSError as e:
                                pass
                            if current_timestamp - ctime >= 60*10 and process_elapse >= 60*5:
                                dead_num += 1
                                process_status = 'Process %-4d task %d/%d PID [%d] seems to be dead. Terminating and restarting process...' % (process_index, group+1, length, process.pid)
                                string = '%s\t%s\n' % (current_time, process_status)
                                log_f.write(string)
                                gone, alive = kill_child_processes(parent_pid = process.pid)
                                process_name = 'user-data-dir=%s' % (user_dir_group)
                                kill_processes_by_name(process_name)
                                process_name = 'log-path=webdriver_%s.log' % (user_dir_group)
                                kill_processes_by_name(process_name)

                                running_processes.remove(process)
                                tasks.append(group)
                                flag = True
                                current_timestamp = time.time()
                    dead_ratio = 1.0 * dead_num / maximum_process_num
                    if len(dead_ratio_list) >= 5:
                        dead_ratio_list.pop(0)
                    dead_ratio_list.append(dead_ratio)
                    avg_dead_ratio = np.mean(dead_ratio_list)
                    if avg_dead_ratio >= 0.2:
                        status = "Too many tasks are dead! Average dead ratio is %.2f!" % (avg_dead_ratio)
                        string = '%s\t%s\n' % (current_time, status)
                        print(string)
                        log_f.write(string)
                        raise TooManyTasksDead("Too many tasks are dead! Average dead ratio is %.2f!" % (avg_dead_ratio))
                if flag == True or (num_alive_processes < maximum_process_num and (len(tasks) > 0 or alive_count % alive_check_timeout == 0)):
                    break
            # We need to get a list. Otherwise, we will receive an exception: RuntimeError: Set changed size during iteration
            #for process in list(running_processes):
            for process in process_list:
                if not process.is_alive():
                    if process in running_processes:
                        running_processes.remove(process)

    except (KeyboardInterrupt, Exception) as e:
        current_time = getlocaltime()
        status = "PARENT SCRIPT exception %s" % type(e)
        string = '%s\t%s\n' % (current_time, status)
        log_f.write(string)
        if not isinstance(e, KeyboardInterrupt) and not isinstance(e, TooManyTasksDead):
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            print(type(e), "PARENT")
            print(''.join('!! ' + line for line in lines))
            status = ''.join('!! ' + line for line in lines)
            string = '%s\t%s\n' % (current_time, status)
            log_f.write(string)
        restart_parent_flag = isinstance(e, TooManyTasksDead)
        if restart_parent_flag:
            os.chdir(script_dir)
        #for process in process_list:
            #try:
                #process.terminate()
            #except Exception:
                #pass

        #process_name = 'chrome'
        #kill_processes_by_name(process_name)
        kill_all_processes(restart_parent_flag)


    while not status_queue.empty():
        process_index, process_status = status_queue.get()
        string = '%s\t%s\n' % (current_time, process_status)
        log_f.write(string)

    for process in process_list:
        try:
            process.join()
        except Exception:
            pass

    gone, alive = kill_child_processes(parent_pid = parent_pid)

    timeout = 10
    while timeout:
        time.sleep(1)
        timeout -= 1
        if not mp.active_children():
            break

    gc_chrome_tmp_files()

    current_time = getlocaltime()
    status = "PARENT SCRIPT COMPLETED! PARENT PID=[%d]" % parent_pid
    string = '%s\t%s\n' % (current_time, status)
    log_f.write(string)
    log_f.close()

def usage():
    tab = '\t'
    print('Usage:')
    print(tab + 'python %s [OPTIONS]' % (__file__))
    print(tab + '-d | --log_dir=')
    print(tab*2 + 'Log directory')
    print(tab + '-u | --user_dir=')
    print(tab*2 + 'User directory of Chrome')
    print(tab + '-i | --input_file=')
    print(tab*2 + 'Input file that contains URLs and ranks')
    print(tab + '-n | --num=')
    print(tab*2 + 'Number of task splits, default is 512')
    print(tab + '-p | --process=')
    print(tab*2 + 'Maximum number of processes, default is 8')
    print(tab + '-t | --type')
    print(tab*2 + 'Input type, [domain|url], default [domain]')
    print(tab + '-s | --start')
    print(tab*2 + 'Start index, default 0')
    print(tab + '-e | --end')
    print(tab*2 + 'End index, default number of URLs')

if __name__ == '__main__':
    main(sys.argv[1:])
