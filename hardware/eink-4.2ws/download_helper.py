import mrequests
import myconfig

my_wdt = None

class ResponseWithProgress(mrequests.Response):
    _total_read = 0

    def readinto(self, buf, size=0):
        bytes_read = super().readinto(buf, size)
        my_wdt.feed()
        self._total_read += bytes_read
        print("Progress: {:.2f}%".format(self._total_read / (self._content_size * 0.01)))
        return bytes_read
    
buf = bytearray(1024)
def download_img(productid=None, scaleid=None):
    global buf
    if productid:
      url = "http://"+myconfig.http_server+":"+str(myconfig.http_server_port)+"/getimage?productid="+str(productid)+"&o=1"
    elif scaleid:
      url = "http://"+myconfig.http_server+":"+str(myconfig.http_server_port)+"/getimage?scaleid="+str(scaleid)+"&o=1"
    else:
      url = "http://"+myconfig.http_server+":"+str(myconfig.http_server_port)+"/getimage?productid=1&o=1" #default

    filename = "img.txt"

    print("Start downloading: ",url," to ",filename)
    try:
      r = mrequests.get(url, headers={b"accept": b"text/plain"}, response_class=ResponseWithProgress)
      if r.status_code == 200:
        r.save(filename, buf=buf)
        print("File saved to '{}'.".format(filename))
      else:
        print("Request failed. Status: {}".format(r.status_code))
      r.close()
    except:
      print("error while downloading.")

def get_config(einkid):
    url = "http://"+myconfig.http_server+":"+str(myconfig.http_server_port)+"/getconfig?id="+einkid
    print("Download config from webserver to identify the assigned scaleid.")

    r = mrequests.get(url, headers={b"Accept": b"application/json"})
    print("Response object instance:")
    print(r)

    myreturn = None
    if r.status_code == 200:
        print("Raw response body:")
        print(r.content)
        print("Response body decoded to string:")
        print(r.text)
        myreturn = r.text
    #    print("Data from decoded from JSON notation in response body:")
    #    print(r.json())
    else:
        print("Request failed. Status: {}".format(r.status_code))

    r.close()

    return myreturn
