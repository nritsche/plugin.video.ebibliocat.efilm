from resources.lib.video.FolderVideo import FolderVideo
from resources.lib.utils.Urls import url_populars


def from_entries(entries):
    folders = []
    seen = set()
    for entry in entries:
        collection = entry.get("list") or {}
        list_id = collection.get("id")
        if not list_id or list_id in seen or not entry.get("count"):
            continue
        seen.add(list_id)
        name = collection.get("name_ca") or collection.get("name")
        if name:
            folders.append(FolderVideo(
                name, "1", "collection:" + str(list_id), "", ""
            ))
    return folders


def getList(strings):
    """Keep all known collections accessible if the live directory is unavailable."""
    folders = []
    for key, url in url_populars.items():
        name = (strings.get(key) if key in ("popular", "noperdis")
                else url.rsplit("/", 1)[-1].replace("-", " ").capitalize())
        list_id = url.split("/lists/", 1)[1].split("/", 1)[0]
        folders.append(FolderVideo(name, "1", "collection:" + list_id, "", ""))
    return folders
