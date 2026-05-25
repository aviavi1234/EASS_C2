import urllib.request
def check_zoom(z):
    try:
        url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/200000/200000?blankTile=false"
        req = urllib.request.Request(url, method='HEAD')
        resp = urllib.request.urlopen(req)
        print(f"Zoom {z}: {resp.status}")
    except Exception as e:
        print(f"Zoom {z}: {e}")

check_zoom(19)
check_zoom(15)
check_zoom(13)
