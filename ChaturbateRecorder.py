import time, datetime, os, sys, requests, configparser, re, subprocess, json
if os.name == 'nt':
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
from queue import Queue
from livestreamer import Livestreamer
from threading import Thread

Config = configparser.ConfigParser()
Config.read(sys.path[0] + "/config.conf")
save_directory = Config.get('paths', 'save_directory')
wishlist = Config.get('paths', 'wishlist')
interval = int(Config.get('settings', 'checkInterval'))
genders = re.sub(' ', '', Config.get('settings', 'genders')).split(",")
directory_structure = Config.get('paths', 'directory_structure').lower()
postProcessingCommand = Config.get('settings', 'postProcessingCommand')
try:
    postProcessingThreads = int(Config.get('settings', 'postProcessingThreads'))
except ValueError:
    pass
completed_directory = Config.get('paths', 'completed_directory').lower()

def now():
    return '[' + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ']'

recording = []

def startRecording(model):
    global postProcessingCommand
    global processingQueue
    try:
        result = requests.get('https://chaturbate.com/api/chatvideocontext/{}/'.format(model)).text
        result = json.loads(result)
        session = Livestreamer()
        session.set_option('http-headers', "referer=https://www.chaturbate.com/{}".format(model))
        streams = session.streams("hlsvariant://{}".format(result['hls_source'].rsplit('?')[0]))
        stream = streams["best"]
        fd = stream.open()
        now = datetime.datetime.now()
        filePath = directory_structure.format(path=save_directory, model=model, gender=result['broadcaster_gender'],
                                              seconds=now.strftime("%S"),
                                              minutes=now.strftime("%M"), hour=now.strftime("%H"),
                                              day=now.strftime("%d"),
                                              month=now.strftime("%m"), year=now.strftime("%Y"))
        directory = filePath.rsplit('/', 1)[0]+'/'
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(filePath, 'wb') as f:
            recording.append(model)
            while True:
                try:
                    data = fd.read(1024)
                    f.write(data)
                except:
                    f.close()
                    recording.remove(model)
                    if postProcessingCommand != "":
                        processingQueue.put({'model':model, 'path':filePath, 'gender':gender})
                    elif completed_directory != "":
                        finishedDir = completed_directory.format(path=save_directory, model=model,
                                                                 gender=gender, seconds=now.strftime("%S"),
                                                                 minutes=now.strftime("%M"),
                                                                 hour=now.strftime("%H"), day=now.strftime("%d"),
                                                                 month=now.strftime("%m"), year=now.strftime("%Y"))

                        if not os.path.exists(finishedDir):
                            os.makedirs(finishedDir)
                        os.rename(filePath, finishedDir+'/'+filePath.rsplit['/',1][0])
                    return

        if model in recording:
            recording.remove(model)
    except:
        if model in recording:
            recording.remove(model)
def postProcess():
    global processingQueue
    global postProcessingCommand
    while True:
        while processingQueue.empty():
            time.sleep(1)
        parameters = processingQueue.get()
        model = parameters['model']
        path = parameters['path']
        filename = path.rsplit('/', 1)[1]
        gender = parameters['gender']
        directory = path.rsplit('/', 1)[0]+'/'
        subprocess.run(postProcessingCommand.split() + [path, filename, directory, model, gender])

def getOnlineModels():
    online = []
    #client = requests.session()
    #client.get('http://www.chaturbate.com/login/')
    #csrftoken = client.cookies['csrftoken']

    data = {"wm": "Hh8qq", "client_ip": "4.4.4.4"}                   
    headers = {
        "Connection": "keep-alive",
     "Origin": "https://www.chaturbate.com",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.52 Safari/536.5",
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Referer": "https://www.chaturbate.com/data/mult.aspx",
"User-Agent" :"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0"}
    result = requests.post("http://chaturbate.com/api/public/affiliates/onlinerooms/", params=data, headers = headers).text
     
    result = json.loads(result)
    #print (  result )        
    length = len(result['results'])
            
    online.extend([m['username'] for m in result['results']])
    #data['key'] = result['key']
            
    f = open(wishlist, 'r')
    wanted =  list(set(f.readlines()))
    wanted = [m.strip('\n').split('chaturbate.com/')[-1].lower().strip().replace('/', '') for m in wanted]
    for theModel in list(set(list(set(wanted).intersection(online))).difference(recording)):
            thread = Thread(target=startRecording, args=(theModel,))
            thread.start()
    f.close()


if __name__ == '__main__':
    AllowedGenders = ['female', 'male', 'trans', 'couple']
    for gender in genders:
        if gender.lower() not in AllowedGenders:
            print(gender, "is not an acceptable gender, options are: female, male, trans, and couple - please correct your config file")
            exit()
    genders = [a.lower()[0] for a in genders]
    print()
    if postProcessingCommand != "":
        processingQueue = Queue()
        postprocessingWorkers = []
        for i in range(0, postProcessingThreads):
            t = Thread(target=postProcess)
            postprocessingWorkers.append(t)
            t.start()
    sys.stdout.write("\033[F")
    while True:
        sys.stdout.write("\033[K")
        print( now(),"{} model(s) are being recorded. Getting list of online models now".format(len(recording)))
        sys.stdout.write("\033[K")
        print("the following models are being recorded: {}".format(recording), end="\r")
        getOnlineModels()
        sys.stdout.write("\033[F")
        for i in range(interval, 0, -1):
            sys.stdout.write("\033[K")
            print(now(), "{} model(s) are being recorded. Next check in {} seconds".format(len(recording), i))
            sys.stdout.write("\033[K")
            print("the following models are being recorded: {}".format(recording), end="\r")
            time.sleep(1)
            sys.stdout.write("\033[F")
