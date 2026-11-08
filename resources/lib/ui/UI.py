from builtins import str
from builtins import object
from resources.lib.utils.Utils import buildUrl
from resources.lib.ebibliocat.EBibliocat import EBibliocat
from resources.lib.ebibliocat.EfilmAPI import EfilmError
from resources.lib.video.FolderVideo import FolderVideo
import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmc
import xbmcvfs
import urllib.parse


class UI(object):

    def __init__(self, base_url, addon_handle, args):
        addon = xbmcaddon.Addon()
        addon_path = xbmcvfs.translatePath(addon.getAddonInfo('path'))
        self.ebiblio = EBibliocat(addon_path, addon)
        self.base_url = base_url
        self.addon_handle = addon_handle
        self.args = args
        self.mode = args.get('mode', None)
        self.url = args.get('url', [''])
        self.name = args.get('name', None)
        xbmc.log("plugin.video.ebibliocat.efilm classe UI - init() ")


    def run(self, mode, url):
        xbmc.log("plugin.video.ebibliocat.efilm classe UI - run()  mode = " + str(mode))


        if mode == None:
            xbmc.log("plugin.ebibliocat.tv3.efilm classe UI - mode = None")
            lFolder = self.ebiblio.listHome()
            account_label = "Sign out of eFilm" if self.ebiblio.session.has_session() else "Sign in to eFilm"
            account_mode = "logout" if self.ebiblio.session.has_session() else "login"
            lFolder.append(FolderVideo(account_label, "", account_mode, "", ""))
            xbmc.log(f"lfolder: {lFolder}")
            if len(lFolder) > 0:
                self.listFolder(lFolder)
            else:
                xbmc.log("UI.run() Home - No existeixen elements")

        elif mode[0] == 'login':
            xbmcplugin.endOfDirectory(self.addon_handle)
            if self.signIn():
                xbmc.executebuiltin(
                    "Container.Update(plugin://plugin.video.ebibliocat.efilm.pitest/)"
                )

        elif mode[0] == 'logout':
            self.ebiblio.signOut()
            xbmcgui.Dialog().notification("eBiblioCat eFilm", "Signed out of eFilm.")
            xbmcplugin.endOfDirectory(self.addon_handle)
            xbmc.executebuiltin("Container.Refresh")

        elif mode[0] in ('lists', 'genres', 'series') or mode[0].startswith('series:'):
            try:
                if mode[0] == 'lists':
                    folders = self.ebiblio.listLists()
                elif mode[0] == 'genres':
                    folders = self.ebiblio.listGenres()
                elif mode[0] == 'series':
                    folders = self.ebiblio.listSeries(int(url[0] or 1))
                else:
                    folders = self.ebiblio.listSeasons(mode[0].split(':', 1)[1])
                self.listFolder(folders)
            except (EfilmError, KeyError, TypeError, ValueError) as error:
                xbmc.log("eFilm directory error: " + str(error), xbmc.LOGERROR)
                xbmcgui.Dialog().notification("eBiblioCat eFilm", "Could not load this directory.")
                self.listFolder([])

        elif mode[0] == 'movies' or mode[0].startswith(('genre:', 'season:')):
            try:
                if mode[0].startswith('season:'):
                    result = self.ebiblio.listEpisodes(mode[0].split(':', 1)[1], url[0])
                else:
                    genre = mode[0].split(':', 1)[1] if ':' in mode[0] else None
                    result = self.ebiblio.listMovies(int(url[0] or 1), genre)
                self.listVideos(result)
            except (EfilmError, KeyError, TypeError, ValueError, OSError) as error:
                xbmc.log("eFilm catalog error: " + str(error), xbmc.LOGERROR)
                xbmcgui.Dialog().notification("eBiblioCat eFilm", "Could not load this catalog.")
                self.listVideos([[], None])

        elif mode[0].startswith('collection:'):
            self.listVideos(self.ebiblio.listCollection(
                mode[0].split(':', 1)[1], int(url[0] or 1)
            ))

        elif mode[0] == 'sections':

            lFolder = self.tv3.programsSections(url[0])

            if len(lFolder) > 0:
                self.listFolder(lFolder)
            else:
                xbmc.log("UI.run() sections - No existeixen elements")

        elif mode[0] == 'dirAZemisio':

            lFolder = self.tv3.dirAZemisio()

            if len(lFolder) > 0:
                self.listFolder(lFolder)
            else:
                xbmc.log("UI.run() dirAZemisio - No existeixen elements")

        elif mode[0] == 'dirAZtots':

            lFolder = self.tv3.dirAZtots()

            if len(lFolder) > 0:
                self.listFolder(lFolder)
            else:
                xbmc.log("UI.run() dirAZtots - No existeixen elements")

        elif mode[0] == 'progAZ':
            letters = self.name[0]
            lFolder = self.tv3.programesAZ(url[0], letters)

            if len(lFolder) > 0:
                self.listFolder(lFolder)
            else:
                xbmc.log("UI.run() progAZ - No existeixen elements")

        elif mode[0] == 'directe':

            lVideos = self.tv3.listDirecte()
            self.listVideos(lVideos)

        elif mode[0] == 'cercar':

            lVideos = self.tv3.search()

            if len(lVideos) > 0:
                self.listVideos(lVideos)
            else:
                xbmc.log("UI.run() cercar - No s'ha trobat cap video")


        elif mode[0] == 'getlistvideos':

            lVideos = self.tv3.getListVideos(url[0], None)
            self.listVideos(lVideos)

        elif mode[0] == 'coleccions':

            lFolder = self.tv3.listColeccions()
            self.listFolder(lFolder)

        elif mode[0] == 'playVideo':
            if url[0].startswith('efilm://episode/'):
                parts = url[0].split('/')
                if len(parts) == 7:
                    self.ebiblio.playProduct(
                        parts[5], parts[6], self.addon_handle,
                        series_id=parts[3], series_slug=parts[4],
                    )
                else:
                    xbmcplugin.setResolvedUrl(self.addon_handle, False, xbmcgui.ListItem())
            elif url[0].startswith('efilm://product/'):
                parts = url[0].split('/')
                if len(parts) >= 5:
                    self.ebiblio.playProduct(parts[-2], parts[-1], self.addon_handle)
                else:
                    xbmcplugin.setResolvedUrl(self.addon_handle, False, xbmcgui.ListItem())
            else:
                self.playVideo(url[0])
        else:
            xbmc.log("plugin.video.ebibliocat.efilm classe UI - mode = las-peliculas-mas-populares")
            lVideos = self.ebiblio.listPopular(mode[0])

            if len(lVideos) > 0:
                self.listVideos(lVideos)
            else:
                xbmc.log("UI.run() popular - No existeixen videos")

    def listFolder(self, lFolderVideos):
        xbmc.log(f"plugin.video.ebibliocat.efilm classe UI - listFolder: {lFolderVideos}")
        for folder in lFolderVideos:

            mode = folder.mode
            name = folder.name
            nameQuoted = urllib.parse.quote(name)
            url = folder.url
            iconImage = folder.iconImage
            thumbImage = folder.thumbnailImage

            urlPlugin = buildUrl({'mode': mode, 'name': nameQuoted, 'url': url}, self.base_url)
            xbmc.log(urlPlugin)
            liz = xbmcgui.ListItem(name)
            liz.setInfo(type="Video", infoLabels={"title": name})
            liz.setArt({'thumb': thumbImage, 'icon' : iconImage})

            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=urlPlugin, listitem=liz, isFolder=True)
        xbmcplugin.endOfDirectory(self.addon_handle)

    def listVideos(self, lVideos):

        xbmc.log("--------List videos ----------")
        last = lVideos[1]
        listVideos = lVideos[0]
        if not listVideos:
            xbmc.log("UI - listVideos - Numero videos: 0")
        else:
            xbmc.log("UI - listVideos - Numero videos: " + str(len(listVideos)))



            for video in listVideos:
                if isinstance(video, FolderVideo):
                    folder_url = buildUrl({
                        'mode': video.mode, 'name': '', 'url': video.url,
                    }, self.base_url)
                    item = xbmcgui.ListItem(video.name)
                    item.setArt({'thumb': video.thumbnailImage, 'icon': video.iconImage})
                    xbmcplugin.addDirectoryItem(
                        handle=self.addon_handle, url=folder_url, listitem=item, isFolder=True,
                    )
                elif video:
                    urlVideo = video.url
                    xbmc.log("UI - listVideos - urlVideo: " + urlVideo)
                    iconImage = video.iconImage
                    thumbImage = video.thumbnailImage
                    durada = video.durada
                    titol = video.title

                    urlPlugin = buildUrl({'mode':'playVideo','name':"",'url':urlVideo}, self.base_url)

                    liz = xbmcgui.ListItem(titol)

                    infolabels = video.information

                    liz.setInfo('video', infolabels)
                    liz.setArt({'thumb': thumbImage, 'icon': "DefaultVideo.png"})
                    liz.addStreamInfo('video', {'duration': durada})
                    liz.setProperty('isPlayable', 'true')
                    xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=urlPlugin, listitem=liz)

            if last:
                mode = last.mode
                name = last.name
                url = last.url
                #xbmc.log("UI - listVideos - urlNext: " + url)
                iconImage = last.iconImage
                thumbImage = last.thumbnailImage

                urlPlugin = buildUrl({'mode': mode, 'name': '', 'url': url}, self.base_url)
                liz = xbmcgui.ListItem(name)
                liz.setInfo(type="Video", infoLabels={"title": name})
                liz.setArt({'thumb': thumbImage, 'icon': iconImage})

                xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=urlPlugin, listitem=liz, isFolder=True)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def signIn(self):
        dialog = xbmcgui.Dialog()
        username = dialog.input("eFilm library username", type=xbmcgui.INPUT_ALPHANUM)
        if not username:
            return
        password = dialog.input(
            "eFilm password",
            type=xbmcgui.INPUT_ALPHANUM,
            option=xbmcgui.ALPHANUM_HIDE_INPUT,
        )
        if not password:
            return
        try:
            self.ebiblio.signIn(username.strip(), password.strip())
            dialog.notification("eBiblioCat eFilm", "Signed in to eFilm.")
            return True
        except EfilmError as error:
            dialog.notification(
                "eBiblioCat eFilm", str(error), xbmcgui.NOTIFICATION_ERROR, 7000
            )
        return False

    def playVideo(self,url):
        code = url[-8:-1]
        xbmc.log("UI - playVideo")


        # html_data = getHtml(url_datavideos + code + '&profile=pc')
        #
        # if html_data:
        #
        #     html_data = html_data.decode("ISO-8859-1")
        #     data = json.loads(html_data)
        #
        #     urlvideo = None
        #
        #     if len(data) > 0:
        #
        #         media = data.get('media', {})
        #
        #         if type(media) is list and len(media) > 0:
        #             media_dict = media[0]
        #             urlvideo = media_dict.get('url', None)
        #         else:
        #             urlvideo = media.get('url', None)
        #
        #         if urlvideo:
        #             if type(urlvideo) is list and len(urlvideo) > 0:
        #                 urlvideo_item = urlvideo[0]
        #                 video = urlvideo_item.get('file', None)
        #
        #             else:
        #                 video = url
        #
        #             xbmc.log("Play video - url:  " + video)

        item = xbmcgui.ListItem(path=url)
        xbmcplugin.setResolvedUrl(self.addon_handle, True, item)
