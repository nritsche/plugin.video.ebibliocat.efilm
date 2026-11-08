from __future__ import division

from builtins import object
import json
import re
import xbmc
import xbmcgui
import xbmcplugin
import urllib.parse
from bs4 import BeautifulSoup


from resources.lib.ebibliocat import DirAZemisio
from resources.lib.ebibliocat import DirAZtots
from resources.lib.ebibliocat import Home
from resources.lib.ebibliocat.Images import Images
from resources.lib.ebibliocat import Sections
from resources.lib.utils import Urls
from resources.lib.video.FolderVideo import FolderVideo
from resources.lib.video.Video import Video
from resources.lib.ebibliocat.EBiblioStrings import EBiblioStrings
from resources.lib.ebibliocat.EfilmAPI import EfilmError, EfilmSession
from resources.lib.ebibliocat.Catalog import movie_page, episode_product
from resources.lib.utils.Utils import *


class EBibliocat(object):
    def __init__(self, addon_path, addon):
        self.strs = EBiblioStrings(addon)
        self.images = Images(addon_path)
        self.addon_path = addon_path
        self.addon = addon
        self.session = EfilmSession(addon)

        xbmc.log("plugin.video.ebibliocat.efilm classe EBibliocat - init() ")

    def signIn(self, username, password):
        self.session.login(username, password)

    def signOut(self):
        self.session.clear()

    def playProduct(self, product_id, slug, handle, series_id=None, series_slug=None):
        def fail(message):
            xbmcgui.Dialog().notification("eBiblioCat eFilm", message, xbmcgui.NOTIFICATION_ERROR, 6000)
            xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())

        try:
            if not self.session.has_session():
                fail("Choose Sign in to eFilm from the add-on menu first.")
                return

            if series_id is not None:
                detail_url = Urls.url_base + "en/series-detail/{}/{}".format(series_id, series_slug)
            else:
                detail_url = Urls.url_base + "en/audiovisual-detail/{}/{}".format(product_id, slug)
            detail_html = getHtml(detail_url)
            if not detail_html:
                fail("Could not load this title from eFilm.")
                return
            detail_soup = BeautifulSoup(detail_html, "html.parser")
            detail_script = detail_soup.find("script", id="__NEXT_DATA__", type="application/json")
            page_props = json.loads(detail_script.string)["props"]["pageProps"]
            product = (episode_product(page_props["collectionProp"], product_id)
                       if series_id is not None else page_props["productInit"])
            self.session.set_localization_from_headers(page_props.get("headers"))

            languages = product.get("languages") or []
            if not languages:
                fail("eFilm has no playable language tracks for this title.")
                return

            options = []
            for track in languages:
                language = track.get("language") or {}
                subtitle = track.get("subtitle") or {}
                language_name = language.get("name_en") or language.get("name") or "Audio"
                subtitle_name = subtitle.get("name_en") or subtitle.get("name") or "Subtitles"
                options.append(("{} — {}".format(language_name, subtitle_name), track))

            selection = 0
            if len(options) > 1:
                selection = xbmcgui.Dialog().select(
                    "Choose audio and subtitles", [option[0] for option in options]
                )
                if selection < 0:
                    xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
                    return

            track = options[selection][1]
            language_id = (track.get("language") or {}).get("id")
            subtitle_id = (track.get("subtitle") or {}).get("id") or 88
            if not language_id:
                fail("eFilm did not provide a language ID for this title.")
                return

            loan_id = self.session.saved_loan(product_id)
            if loan_id:
                confirm = xbmcgui.Dialog().yesno(
                    "Resume eFilm loan",
                    "Resume your existing loan for {}?".format(product.get("name", "this title")),
                    nolabel="Cancel",
                    yeslabel="Resume",
                )
            else:
                confirm = xbmcgui.Dialog().yesno(
                    "Borrow from eFilm",
                    "Borrow {}? This uses one of your available eFilm loans.".format(
                        product.get("name", "this title")
                    ),
                    nolabel="Cancel",
                    yeslabel="Borrow",
                )
            if not confirm:
                xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
                return

            if not loan_id:
                loan = self.session.make_loan(product_id)
                loan_id = loan["id"]
                self.session.save_loan(product_id, loan_id)

            playback = self.session.get_playback(loan_id, language_id, subtitle_id)
            item = self._makePlaybackItem(playback, product)
            if not item:
                fail("eFilm approved the loan but did not provide a Kodi-compatible stream.")
                return
            xbmcplugin.setResolvedUrl(handle, True, item)
        except EfilmError as error:
            fail(str(error))
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            xbmc.log("eFilm playback response could not be parsed: " + str(error), xbmc.LOGERROR)
            fail("eFilm returned an unexpected playback response. Check the Kodi log.")

    def _makePlaybackItem(self, playback, product):
        if isinstance(playback, str):
            try:
                playback = json.loads(playback)
            except ValueError:
                xbmc.log("eFilm playback response is a string, not JSON", xbmc.LOGERROR)
                return None
        if isinstance(playback, list):
            playback = playback[0] if playback else {}
        if not isinstance(playback, dict):
            xbmc.log("eFilm playback response type: " + type(playback).__name__, xbmc.LOGERROR)
            return None
        if isinstance(playback.get("data"), dict):
            playback = playback["data"]
        player = playback.get("player") or {}
        if isinstance(player, str):
            try:
                player = json.loads(player)
            except ValueError:
                player = {"source": player}
        if not isinstance(player, dict):
            xbmc.log("eFilm player response type: " + type(player).__name__, xbmc.LOGERROR)
            return None
        source = player.get("source") or {}
        if isinstance(source, str):
            try:
                source = json.loads(source)
            except ValueError:
                source = {"src": source}
        if not isinstance(source, dict):
            xbmc.log("eFilm source response type: " + type(source).__name__, xbmc.LOGERROR)
            return None
        streaming = source.get("data_streaming") or {}
        if isinstance(streaming, list):
            streaming = streaming[0] if streaming else {}
        if not isinstance(streaming, dict):
            streaming = {}

        stream_url = None
        stream_key = None
        direct = source.get("src")
        if isinstance(direct, str) and direct.startswith(("https://", "http://")):
            stream_url = direct
            stream_key = "src"
        for key in ("src", "url", "file", "DASHURL", "HLSURL", "FLVURL"):
            if stream_url:
                break
            value = streaming.get(key) or source.get(key)
            if isinstance(value, str) and value.startswith(("https://", "http://")):
                stream_url = value
                stream_key = key
                break
        if not stream_url:
            xbmc.log(
                "eFilm playback fields: top={} player={} source={} streaming={}".format(
                    sorted(playback.keys()), sorted(player.keys()), sorted(source.keys()),
                    sorted(streaming.keys()) if isinstance(streaming, dict) else type(streaming).__name__
                ),
                xbmc.LOGERROR,
            )
            return None

        stream_type = str(
            streaming.get("type")
            or streaming.get("manifest_type")
            or source.get("type")
            or stream_key
            or ""
        ).lower()
        if ".mpd" in stream_url.lower() or "dash" in stream_type:
            manifest_type = "mpd"
            mime_type = "application/dash+xml"
        elif ".m3u8" in stream_url.lower() or any(
            value in stream_type for value in ("hls", "flvurl", "mpegurl")
        ):
            manifest_type = "hls"
            mime_type = "application/vnd.apple.mpegurl"
        else:
            manifest_type = None
            mime_type = "video/mp4" if ".mp4" in stream_url.lower() else ""

        item = xbmcgui.ListItem(path=stream_url)
        item.setInfo("video", {"title": product.get("name", "eFilm video")})
        if mime_type:
            item.setMimeType(mime_type)

        license_url = (
            streaming.get("license_url")
            or streaming.get("licenseUrl")
            or source.get("license_url")
            or source.get("licenseUrl")
        )
        if manifest_type:
            item.setProperty("inputstream", "inputstream.adaptive")
            item.setProperty("inputstream.adaptive.manifest_type", manifest_type)
            item.setProperty("IsPlayable", "true")
            item.setContentLookup(False)

            stream_headers = streaming.get("headers") or source.get("headers")
            if isinstance(stream_headers, dict) and stream_headers:
                item.setProperty(
                    "inputstream.adaptive.stream_headers",
                    urllib.parse.urlencode(stream_headers),
                )

            if license_url:
                drm_type = str(
                    streaming.get("license_type") or streaming.get("drm_type") or streaming.get("type") or ""
                ).lower()
                if "playready" in drm_type:
                    license_type = "com.microsoft.playready"
                elif "fairplay" in drm_type:
                    return None
                else:
                    license_type = "com.widevine.alpha"
                item.setProperty("inputstream.adaptive.license_type", license_type)
                license_headers = streaming.get("license_headers") or source.get("license_headers")
                if isinstance(license_headers, dict) and license_headers:
                    license_key = "{}|{}|R{{SSM}}|".format(
                        license_url, urllib.parse.urlencode(license_headers)
                    )
                else:
                    license_key = license_url
                item.setProperty("inputstream.adaptive.license_key", license_key)

        return item

    def listHome(self):
        return [FolderVideo(name, "1", mode, "", "") for name, mode in (
            ("All movies (A–Z)", "movies"), ("Movies by genre", "genres"),
            ("Lists", "lists"), ("Series", "series"),
        )]

    def listLists(self):
        try:
            entries = self.session.visible_lists()
            folders = Home.from_entries(entries)
            if folders:
                return folders
        except (EfilmError, AttributeError, KeyError, TypeError, ValueError) as error:
            xbmc.log("eFilm collection directory unavailable: " + str(error), xbmc.LOGWARNING)
        return Home.getList(self.strs)

    def listCollection(self, list_id, page=1):
        videos = []
        next_folder = None
        try:
            result = self.session.list_elements(list_id, page)
            for entry in result["results"]:
                series = entry.get("collections")
                if series and series.get("type") == "serie":
                    videos.append(FolderVideo(
                        series["name"], "1", "series:" + str(series["id"]),
                        series.get("cover") or "", series.get("cover") or "",
                    ))
                    continue
                product = entry.get("products") or {}
                if product.get("type") != "audiovisual":
                    continue
                # Full metadata and language tracks are loaded when playback starts.
                product = dict(product, languages=[])
                video = self.getVideo(product)
                if video:
                    videos.append(video)
            if (result.get("links") or {}).get("next"):
                next_folder = FolderVideo(
                    "Next page", str(page + 1), "collection:" + str(list_id), "", ""
                )
        except (EfilmError, AttributeError, KeyError, TypeError, ValueError) as error:
            xbmc.log("eFilm collection load failed: " + str(error), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                "eBiblioCat eFilm", "Could not load this collection. Try again.",
                xbmcgui.NOTIFICATION_ERROR, 6000,
            )
        return [videos, next_folder]

    def listMovies(self, page=1, genre_id=None):
        products, has_next = movie_page(self.session.movies(), page, genre_id)
        videos = [self.getVideo(dict(p, languages=[])) for p in products]
        mode = "movies" if genre_id is None else "genre:" + str(genre_id)
        following = (FolderVideo("Next page", str(page + 1), mode, "", "")
                     if has_next else None)
        return [videos, following]

    def listGenres(self):
        return [FolderVideo(g["name"], "1", "genre:" + str(g["id"]), "", "")
                for g in self.session.genres()]

    def listSeries(self, page=1):
        result = self.session.series(page)
        folders = [FolderVideo(
            p["name"], "1", "series:" + str(p["id"]), p.get("cover") or "",
            p.get("cover") or "",
        ) for p in result["results"]]
        if (result.get("links") or {}).get("next"):
            folders.append(FolderVideo("Next page", str(page + 1), "series", "", ""))
        return folders

    def listSeasons(self, series_id):
        detail = self.session.series_detail(series_id)
        return [FolderVideo(
            "Season " + str(season["season"]), str(season["season"]),
            "season:" + str(series_id), detail.get("cover") or "",
            detail.get("cover") or "",
        ) for season in detail.get("seasons", []) if season.get("chapters")]

    def listEpisodes(self, series_id, season_number):
        detail = self.session.series_detail(series_id)
        videos = []
        for season in detail.get("seasons", []):
            if str(season["season"]) == str(season_number):
                for product in season.get("chapters", []):
                    video = self.getVideo(dict(product, languages=[]))
                    if video:
                        video.url = "efilm://episode/{}/{}/{}/{}".format(
                            series_id, detail.get("slug") or "series",
                            product["id"], product.get("slug") or "episode",
                        )
                        videos.append(video)
                break
        return [videos, None]

    # mode = destaquem
    def listPopular(self, section):
        lVideos = []
        html = getHtml(Urls.url_populars[section])
        if not html:
            xbmc.log("eFilm could not load list: " + section, xbmc.LOGERROR)
            return [lVideos, None]

        try:
            soup = BeautifulSoup(html, "html.parser")
            script = soup.find('script', id="__NEXT_DATA__", type="application/json")
            entries = json.loads(script.string)["props"]["pageProps"]["productsProp"]["results"]
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            xbmc.log("eFilm list parse error for " + section + ": " + str(error), xbmc.LOGERROR)
            return [lVideos, None]

        for entry in entries:
            try:
                product = entry["products"]
                detail_url = (
                    Urls.url_base + "en/audiovisual-detail/" +
                    str(product["id"]) + "/" + product["slug"]
                )
                detail_html = getHtml(detail_url)
                if not detail_html:
                    continue
                detail_soup = BeautifulSoup(detail_html, "html.parser")
                detail_script = detail_soup.find('script', id="__NEXT_DATA__", type="application/json")
                detail = json.loads(detail_script.string)["props"]["pageProps"]["productInit"]
                video = self.getVideo(detail)
                if video:
                    lVideos.append(video)
            except (AttributeError, KeyError, TypeError, ValueError) as error:
                xbmc.log("eFilm item parse error: " + str(error), xbmc.LOGWARNING)

        xbmc.log("eFilm list " + section + " contains " + str(len(lVideos)) + " titles", xbmc.LOGINFO)

        result = [None] * 2
        result[0] = lVideos
        return result


    # mode = noperdis
    def listNoPerdis(self):
        xbmc.log("--------------listNoPerdis----------")

        lVideos = []

        link = getHtml(Urls.url_coleccions)

        if link:

            soup = BeautifulSoup(link, "html.parser")

            try:
                links = soup.findAll("li", {"class": "sensePunt R-elementLlistat  C-llistatVideo"})

                if not links:
                    links = soup.findAll("li", {"class": "sensePunt R-elementLlistat  C-llistatVideo "})

                if not links:
                    links = soup.findAll("li", {"class": "sensePunt R-elementLlistat  C-llistatVideo  "})

                for i in links:
                    a = i.a["href"]
                    code = a[-8:-1]

                    link = getHtml(Urls.url_datavideos + code + '&profile=pc')

                    link = link.decode("ISO-8859-1")
                    data = json.loads(link)

                    if len(data) > 0:
                        video = self.getVideo(data)
                        lVideos.append(video)

            except AttributeError as e:
                xbmc.log("Exception AtributeError NoPerdis: " + str(e))
            except KeyError as e:
                xbmc.log("Exception KeyError NoPerdis: " + str(e))
            except Exception as e:
                xbmc.log("Exception Item destacat: " + str(e))

        result = [None] * 2
        result[0] = lVideos
        return result


    # mode = mesvist
    def listMesVist(self):
        xbmc.log("--------------listMesVist----------")

        lVideos = []

        link = getHtml(Urls.url_mesvist)

        if link:

            soup = BeautifulSoup(link, "html.parser")

            try:
                links = soup.findAll("li", {"class": re.compile("C-llistatVideo")})

                for i in links:
                    a = i.a["href"]
                    code = a[-8:-1]

                    link = getHtml(Urls.url_datavideos + code + '&profile=pc')

                    link = link.decode("ISO-8859-1")
                    data = json.loads(link)



                    if len(data) > 0:
                        video = self.getVideo(data)
                        lVideos.append(video)

            except AttributeError as e:
                xbmc.log("Exception AtributeError listMesVist: " + str(e))
            except KeyError as e:
                xbmc.log("Exception KeyError listMesVist: " + str(e))
            except Exception as e:
                xbmc.log("Exception listMesVist: " + str(e))

        result = [None] * 2
        result[0] = lVideos
        return result



    # mode = coleccions
    def listColeccions(self):
        xbmc.log("--------------listColeccions----------")

        lFolderVideos = []

        link = getHtml(Urls.url_coleccions)

        if link:

            soup = BeautifulSoup(link, "html.parser")

            try:

                colecc = soup.findAll("div", {"class": re.compile("M-destacat")})


                for el in colecc:

                    url = el.a["href"]
                    url = Urls.url_base + url
                    t = el.div.h2.a.string

                    titol = t.encode("utf-8")


                    img = el.figure.img["src"]


                    foldVideo = FolderVideo(titol,url, 'getlistvideos', img, img)
                    lFolderVideos.append(foldVideo)

            except AttributeError as e:
                xbmc.log("Exception AtributeError listColeccions: " + str(e))
            except KeyError as e:
                xbmc.log("Exception KeyError listColeccions: " + str(e))
            except Exception as e:
                xbmc.log("Exception listColeccions: " + str(e))


        return lFolderVideos


    # mode = programes
    def dirSections(self):

        return Sections.getList(self.strs)

    # mode = dirAZemisio
    def dirAZemisio(self):

        return DirAZemisio.getList()

    #mode = dirAZtots
    def dirAZtots(self):

        return DirAZtots.getList()

    # mode = sections
    def programsSections(self, url):
        xbmc.log("-------------------------programsSections----------------------")
        lFolderVideos = []

        link = getHtml(Urls.url_programes_emisio + url)

        if link:
            soup = BeautifulSoup(link)

            try:
                # Grups programes de cada lletra
                links = soup.findAll("ul", {"class": "R-abcProgrames"})

                for i in links:
                    ls = i.findAll("li")

                    for li in ls:
                        url = li.a["href"]
                        t = str(li.a.string)
                        titol = re.sub('^[\n\r\s]+', '', t)

                        # test url
                        urlProg = Urls.url_base + url
                        if urlProg == Urls.urlApm or urlProg == Urls.urlZonaZaping:
                            url_final = urlProg + 'clips/'

                        elif 'super3' in url:
                            if 'https:' not in url:
                                url_final = 'https:' + url
                            else:
                                url_final = url


                        else:
                            match = re.compile('(http://www.ccma.cat/tv3/alacarta/.+?/fitxa-programa/)(\d+/)').findall(
                                urlProg)
                            if len(match) != 0:
                                url1 = match[0][0]
                                urlcode = match[0][1]
                                url_final = url1 + 'capitols/' + urlcode
                            else:
                                url_final = urlProg + 'capitols/'


                        foldVideo = FolderVideo(titol, url_final, 'getlistvideos', "", "")
                        lFolderVideos.append(foldVideo)

            except AttributeError as e:
                xbmc.log("Exception AtributeError listSections: " + str(e))
            except KeyError as e:
                xbmc.log("Exception KeyError listSections: " + str(e))
            except Exception as e:
                xbmc.log("Exception listSections: " + str(e))

        return lFolderVideos


    # mode = directe
    def listDirecte(self):
        xbmc.log("-----------------listDirecte--------------------")
        lVideos = []

        data = getDataVideo(Urls.url_arafem)

        if data:
            c = data.get('canal', None)

            if c:

                arafemtv3 = ''
                arafem33 = ''
                arafemesp3 = ''
                arafem324 = ''
                arafemtv3_sinop = ''
                arafem33_sinop = ''
                arafemesp3_sinop = ''
                arafem324_sinop = ''

                i = 0
                while i < 5:
                    nameChannel = c[i].get('ara_fem', {}).get('codi_canal', None)

                    if nameChannel == 'tv3':
                        arafemtv3 = c[i].get('ara_fem', {}).get('titol_programa', None)
                        arafemtv3_sinop = c[i].get('ara_fem', {}).get('sinopsi', None)
                    if nameChannel == 'cs3' or nameChannel == '33d':
                        arafem33 = c[i].get('ara_fem', {}).get('titol_programa', None)
                        arafem33_sinop = c[i].get('ara_fem', {}).get('sinopsi', None)
                    if nameChannel == 'esport3':
                        arafemesp3 = c[i].get('ara_fem', {}).get('titol_programa', None)
                        arafemesp3_sinop = c[i].get('ara_fem', {}).get('sinopsi', None)
                    if nameChannel == '324':
                        arafem324 = c[i].get('ara_fem', {}).get('titol_programa', None)
                        arafem324_sinop = c[i].get('ara_fem', {}).get('sinopsi', None)

                    i = i + 1

            infolabelstv3 = {}
            infolabels324 = {}
            infolabels33 = {}
            infolabelsesp3 = {}

            if arafemtv3:
                infolabelstv3['title'] = arafemtv3
                infotv3 = '[B]' + arafemtv3 + '[/B]' + '[CR]'
            if arafemtv3_sinop:
                if type(arafemtv3) is int or type(arafemtv3) is float:
                    arafemtv3 = str(arafemtv3)
                infotv3 = infotv3 + arafemtv3_sinop

            infolabelstv3['plot'] = infotv3

            if arafem33:
                infolabels33['title'] = arafem33
                info33 = '[B]' + arafem33 + '[/B]' + '[CR]'
            if arafem33_sinop:
                if type(arafem33) is int or type(arafem33) is float:
                    arafem33 = str(arafem33)
                info33 = info33 + arafem33_sinop

            infolabels33['plot'] = info33

            if arafemesp3:
                infolabelsesp3['title'] = arafemesp3
                infoesp3 = '[B]' + arafemesp3 + '[/B]' + '[CR]'
            if arafemesp3_sinop:
                if type(arafemesp3) is int or type(arafemesp3) is float:
                    arafemesp3 = str(arafemesp3)
                infoesp3 = infoesp3 + arafemesp3_sinop

            infolabelsesp3['plot'] = infoesp3

            if arafem324:
                infolabels324['title'] = arafem324
                info324 = '[B]' + arafem324 + '[/B]' + '[CR]'
            if arafem324_sinop:
                if type(arafem324) is int or type(arafem324) is float:
                    arafem324 = str(arafem324)
                info324 = info324 + arafem324_sinop

            infolabels324['plot'] = info324

        tv3Directe = Video(self.strs.get('tv3'), self.images.thumb_tv3, self.images.thumb_tv3, infolabelstv3, Urls.url_directe_tv3, "")
        c324Directe = Video(self.strs.get('canal324'), self.images.thumb_tv3, self.images.thumb_tv3, infolabels324, Urls.url_directe_324, "")
        c33s3Directe = Video(self.strs.get('c33super3'), self.images.thumb_tv3, self.images.thumb_tv3, infolabels33, Urls.url_directe_c33s3, "")
        sps3Directe = Video(self.strs.get('esport3'), self.images.thumb_tv3, self.images.thumb_tv3, infolabelsesp3, Urls.url_directe_esport3, "")

        tv3DirecteInt = Video(self.strs.get('tv3_int'), self.images.thumb_tv3, self.images.thumb_tv3, infolabelstv3, Urls.url_directe_tv3_int, "")
        c324DirecteInt = Video(self.strs.get('canal324_int'), self.images.thumb_tv3, self.images.thumb_tv3, infolabels324, Urls.url_directe_324_int, "")
        c33s3DirecteInt = Video(self.strs.get('c33super3_int'), self.images.thumb_tv3, self.images.thumb_tv3, infolabels33, Urls.url_directe_c33s3_int, "")
        sps3DirecteInt = Video(self.strs.get('esport3_int'), self.images.thumb_tv3, self.images.thumb_tv3, infolabelsesp3, Urls.url_directe_esport3_int, "")

        lVideos = [tv3Directe, c33s3Directe, c324Directe, sps3Directe, tv3DirecteInt, c33s3DirecteInt, c324DirecteInt, sps3DirecteInt]

        result = [None] * 2
        result[0] = lVideos
        return result


    # mode = progAZ
    def programesAZ(self, paramUrl, letters):
        xbmc.log("--------------------programesAZ------------------")
        letters = urllib.parse.unquote(letters)
        lFolderVideos = []
        url = ""

        if paramUrl == "emisio":
            url = Urls.url_programes_emisio
        else:
            url = Urls.url_programes_tots

        html = getHtml(url)


        if html:

            soup = BeautifulSoup(html.decode('utf-8', 'ignore'), "html.parser")

            elements = soup.findAll("ul", {"class": "R-abcProgrames"})

            li = None


            if len(elements) > 0:

                if letters == "#A-C":

                    li = elements[0:4]

                elif letters == "D-E":

                    li = elements[4:6]

                elif letters == "F-I":

                    li = elements[6:10]

                elif letters == "J-L":

                    li = elements[10:13]

                elif letters == "M-P":

                    li = elements[13:17]

                elif letters == "Q-S":

                    li = elements[17:20]

                elif letters == "T-V":

                    li = elements[20:23]

                elif letters == "X-Z":

                    li = elements[23:]

                if li != None and len(li) > 0:

                    for l in li:

                        links = l.findAll("li")

                        if len(links) > 0:

                            for i in links:
                                #xbmc.log("progsAZ - li: " + str(i).encode('utf-8'))

                                url = i.a["href"]
                                titol = i.a.string.strip().encode("utf-8")

                                # test url
                                urlProg = Urls.url_base + url
                                if urlProg == Urls.urlApm or urlProg == Urls.urlZonaZaping:
                                    url_final = urlProg + 'clips/'

                                elif 'super3' in url:
                                    if 'https:' not in url:
                                        url_final = 'https:' + url
                                    else:
                                        url_final = url

                                else:
                                    match = re.compile(
                                        '(http://www.ccma.cat/tv3/alacarta/.+?/fitxa-programa/)(\d+/)').findall(urlProg)
                                    if len(match) != 0:
                                        url1 = match[0][0]
                                        urlcode = match[0][1]
                                        url_final = url1 + 'capitols/' + urlcode
                                    else:
                                        url_final = urlProg + 'capitols/'

                                folderVideo = FolderVideo(titol, url_final, 'getlistvideos', "", "")
                                lFolderVideos.append(folderVideo)
                                #xbmc.log("progsAZ - Titol: " + titol)
                                #xbmc.log("progsAZ - url: " + url_final)


        return  lFolderVideos

    # mode = getlistvideos
    def getListVideos(self, url, cercar):
        xbmc.log("---------------getListVideos------------------------------")
        result = [None] * 2
        lVideos = []

        xbmc.log('getListVideos--Url listvideos: ' + url)

        link = getHtml(url)

        if link:

            soup = BeautifulSoup(link.decode('utf-8', 'ignore'), "html.parser")

            links = None
            try:
                links = soup.findAll("div", {"class": "F-itemContenidorIntern C-destacatVideo"})

                if not links:
                    links = soup.findAll("li", {"class": "F-llistat-item"})

                # Coleccions
                if not links:
                    links = soup.findAll("div", {"class": re.compile("M-destacat")})

                # Zona Zapping
                if not links:
                    links = soup.findAll("article", {"class": "M-destacat  C-destacatVideo T-alacartaTema C-3linies "})

                # Super 3
                if not links:
                    links = soup.findAll("div",
                                         {"class": "M-destacat super3 T-video  ombres-laterals"})
                    links2 = soup.findAll("div",
                                         {"class": "M-destacat super3 noGapAfter T-video  ombres-laterals"})
                    links = links + links2

                # Super 3
                if not links:
                    links = soup.findAll("article",
                                         {"class": "M-destacat super3 noGapAfter T-video  ombres-laterals"})


            except AttributeError as e:
                xbmc.log("getListVideos--getLinks--Exception AtributeError listVideos: " + str(e))
            except KeyError as e:
                xbmc.log("getListVideos--getLinks--Exception KeyError  listVideos: " + str(e))
            except Exception as e:
                xbmc.log("getListVideos--getLinks--Exception listVideos: " + str(e))

            if links:

                for l in links:

                    try:

                        urlvideo = l.a["href"]

                        code = urlvideo.split('/')[-1]

                        if len(code) == 0:
                            code = urlvideo.split('/')[-2]


                        html_data = getHtml(Urls.url_datavideos + code + '&profile=pc')

                        html_data = html_data.decode("ISO-8859-1")
                        data = json.loads(html_data)

                        if len(data) > 0:
                            video = self.getVideo(data)
                            lVideos.append(video)




                    except AttributeError as e:
                        xbmc.log("getListVideos--bucle addVideo--Exception AtributeError: " + str(e))

                    except KeyError as e:
                        xbmc.log("getListVideos--bucle addVideo--Exception KeyError: " + str(e))

                    except Exception as e:
                        xbmc.log("getListVideos--bucle addVideo--Exception: " + str(e))

                result[0] = lVideos

                ###############################################################################

                # Pagination
                ht = rb'<p class="numeracio">P\xc3\xa0gina (\d+) de (\d+)</p>'

                match = re.compile(ht).findall(link)
                if len(match) != 0:
                    actualPage = int(match[0][0])
                    totalPages = int(match[0][1])

                    if actualPage < totalPages:
                        ntPage = str(actualPage + 1)
                        nextPage = '&pagina=' + ntPage
                        if cercar:
                            if actualPage == 1:
                                url_next = url + nextPage
                            else:
                                url_next = re.sub('&pagina=[\d]+', nextPage, url)
                        else:
                            url_next = url + '?text=&profile=&items_pagina=15' + nextPage
                            foldNext = FolderVideo(self.strs.get('seguent'), url_next, "getlistvideos", "","")
                            foldNext.hasNextPage = True
                            result[1] = foldNext

        return result


    def getVideo(self, data):
        product_id = data.get("id")
        slug = data.get("slug") or ""
        streaming = data.get("streaming") or {}
        stream_url = streaming.get("url") or streaming.get("file")
        is_efilm_product = product_id is not None and "languages" in data
        if is_efilm_product:
            urlVideo = "efilm://product/{}/{}".format(product_id, slug)
        else:
            urlVideo = data.get("url_embedded") or stream_url or data.get("trailer")
        if not urlVideo:
            return None

        titol = data.get("name") or data.get("name_en") or data.get("name_es") or "eFilm video"
        image = data.get("cover") or ""
        descripcio = data.get("description") or ""
        programa = None
        capitol = None
        genres = data.get('genres') or []
        tematica = genres[0].get('name') if genres else None
        data_emisio = None
        minutes = data.get("duration")
        durada = ""
        trailerUrl = data.get("trailer")

        if minutes != None:
            durada = minutes * 60


        if descripcio == None:
            descripcio = ''
        else:
            descripcio = descripcio.replace('<br />', '')

        header = ""
        if programa != None:
            if type(programa) is int or type(programa) is float:
                programa = str(programa)
            header = '[B]' + programa + '[/B]' + '[CR]'

        infolabels = {}
        if data_emisio != None:
            dt = data_emisio[0:10]
            year = data_emisio[6:10]
            infolabels['aired'] = dt
            infolabels['year'] = year
            header = header + dt + '[CR]'

        descripcio = header + descripcio

        if titol != None:
            infolabels['title'] = titol


        if capitol != None:
            infolabels['episode'] = capitol


        if descripcio != None:
            infolabels['plot'] = descripcio

        if tematica != None:
            infolabels['genre'] = tematica

        if trailerUrl != None:
            infolabels["trailer"] = trailerUrl

        video = Video(titol, image, image, infolabels, urlVideo, durada)
        if is_efilm_product:
            video.product_id = product_id
            video.slug = slug
        return video

    #mode = cercar
    def search(self):

        keyboard = xbmc.Keyboard('', self.strs.get('cercar'))
        keyboard.doModal()
        if keyboard.isConfirmed() and keyboard.getText():
            search_string = keyboard.getText().replace(" ", "+")
            url = "http://www.ccma.cat/tv3/alacarta/cercador/?items_pagina=15&profile=videos&text=" + search_string

            lVideos = self.getListVideos(url, True)

        return lVideos

