from resources.lib.video.FolderVideo import FolderVideo
from resources.lib.utils.Urls import url_coleccions, url_mesvist



def getList(strings):

    popular = FolderVideo(strings.get('popular'), "", "popular", "", "")
    noperdis = FolderVideo(strings.get('noperdis'), "", "noperdis", "", "")
    drama = FolderVideo(strings.get('drama'), url_mesvist, "drama", "", "")
    coleccions = FolderVideo(strings.get('coleccions'), "", "coleccions", "", "")
    programes = FolderVideo(strings.get('programes'), "", "programes", "", "")
    directe = FolderVideo(strings.get('directe'), "", "directe", "", "")
    cercar = FolderVideo(strings.get('cercar'), "", "cercar", "", "")

    list = [popular, noperdis]#, coleccions, programes, directe, cercar]

    return list