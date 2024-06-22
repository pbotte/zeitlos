import mrequests

my_wdt = None

class ResponseWithProgress(mrequests.Response):
    _total_read = 0

    def readinto(self, buf, size=0):
        bytes_read = super().readinto(buf, size)
        my_wdt.feed()
        self._total_read += bytes_read
        print("Progress: {:.2f}%".format(self._total_read / (self._content_size * 0.01)))
        return bytes_read
    
def download_img(productid=None, scaleid=None):
    buf = bytearray(1024)
    if productid:
      url = "http://192.168.178.242:8090/getimage?productid="+str(productid)+"&o=1"
    elif scaleid:
      url = "http://192.168.178.242:8090/getimage?scaleid="+str(scaleid)+"&o=1"
    else:
      url = "http://192.168.178.242:8090/getimage?productid=1&o=1" #default

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

def download_config(einkid):
    buf = bytearray(1024)
    url = "http://192.168.178.242:8090/getconfig?id="+einkid

    filename = "myconfig_assigned_scale.txt"

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
