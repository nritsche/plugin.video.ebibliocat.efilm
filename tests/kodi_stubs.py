"""Explicit Kodi boundary doubles; tests import the real application modules."""

import sys
import types
from pathlib import Path
from unittest.mock import Mock


class ListItem:
    def __init__(self, label="", path="", **kwargs):
        self.label, self.path = label, path
        self.properties, self.info, self.art = {}, {}, {}
        self.mime, self.lookup = None, None
        self.tag = Mock()

    def setProperty(self, key, value):
        self.properties[key] = value

    def setPath(self, path):
        self.path = path

    def setMimeType(self, value):
        self.mime = value

    def setContentLookup(self, value):
        self.lookup = value

    def setInfo(self, kind, info):
        self.info.update(info)

    def setArt(self, art):
        self.art.update(art)

    def getVideoInfoTag(self):
        return self.tag


class Addon:
    def __init__(self, profile="/tmp/efilm-unit-profile"):
        self.profile = str(profile)

    def getAddonInfo(self, key):
        return {
            "profile": self.profile,
            "path": str(Path(__file__).resolve().parents[1]),
            "id": "plugin.video.ebibliocat.efilm",
            "version": "0.2.0",
        }[key]

    def getLocalizedString(self, code):
        return ""  # Exercise real built-in English fallbacks, not arbitrary mock labels.


def install():
    if getattr(sys.modules.get("xbmc"), "_efilm_stub", False):
        return
    xbmc = types.ModuleType("xbmc")
    xbmc._efilm_stub = True
    xbmc.LOGDEBUG, xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 0, 1, 2, 3
    xbmc.ISO_639_1 = 0
    xbmc.log = Mock()
    xbmc.getLanguage = Mock(return_value="en")
    xbmc.getInfoLabel = Mock(return_value="21.2")
    xbmc.getCondVisibility = Mock(return_value=False)
    xbmc.executebuiltin = Mock()
    xbmc.Monitor = Mock(return_value=Mock(abortRequested=Mock(return_value=False)))
    xbmcgui = types.ModuleType("xbmcgui")
    xbmcgui.ListItem = ListItem
    xbmcgui.NOTIFICATION_ERROR = "error"
    xbmcgui.NOTIFICATION_INFO = "info"
    xbmcgui.INPUT_ALPHANUM = 0
    xbmcgui.ALPHANUM_HIDE_INPUT = 1
    xbmcgui.Dialog = Mock(return_value=Mock(yesno=Mock(return_value=True), select=Mock(return_value=0)))
    xbmcgui.DialogProgress = Mock(return_value=Mock(iscanceled=Mock(return_value=False)))
    plugin = types.ModuleType("xbmcplugin")
    for name in ("setContent", "endOfDirectory", "setResolvedUrl", "addDirectoryItem", "setPluginCategory"):
        setattr(plugin, name, Mock())
    addon = types.ModuleType("xbmcaddon")
    addon.Addon = Mock(side_effect=Addon)
    vfs = types.ModuleType("xbmcvfs")
    vfs.translatePath = lambda path: str(path)
    helper = types.ModuleType("inputstreamhelper")
    helper.Helper = Mock(return_value=Mock(check_inputstream=Mock(return_value=True)))
    sys.modules.update(
        xbmc=xbmc, xbmcgui=xbmcgui, xbmcplugin=plugin, xbmcaddon=addon, xbmcvfs=vfs, inputstreamhelper=helper
    )
