from resources.lib.video.FolderVideo import FolderVideo
from resources.lib.utils.Urls import url_coleccions, url_mesvist



def getList(strings):

    popular = FolderVideo(strings.get('popular'), "", "las-peliculas-mas-populares", "", "")
    #noperdis = FolderVideo(strings.get('noperdis'), url_coleccions, "noperdis", "", "")
    mesvist = FolderVideo(strings.get('mesvist'), url_mesvist, "mesvist", "", "")
    coleccions = FolderVideo(strings.get('coleccions'), "", "coleccions", "", "")
    programes = FolderVideo(strings.get('programes'), "", "programes", "", "")
    directe = FolderVideo(strings.get('directe'), "", "directe", "", "")
    cercar = FolderVideo(strings.get('cercar'), "", "cercar", "", "")

    list = [popular]#, mesvist, coleccions, programes, directe, cercar]

    return list