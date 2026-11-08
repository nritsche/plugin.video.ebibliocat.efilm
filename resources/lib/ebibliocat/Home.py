from resources.lib.video.FolderVideo import FolderVideo


def getList(strings):
    popular = FolderVideo(strings.get('popular'), "", "popular", "", "")
    noperdis = FolderVideo(strings.get('noperdis'), "", "noperdis", "", "")
    return [popular, noperdis]
