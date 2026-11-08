from __future__ import absolute_import

import json
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.request

import xbmcvfs


API_BASE = "https://backend-prod.efilm.online/api/v1/"
EBIBLIOCAT_CLIENT_ID = 5
LANGUAGE = "ca"
DEFAULT_LOCALIZATION = {"codeCountry": "ES", "city": "", "test": 2}


class EfilmError(Exception):
    def __init__(self, message, status=None):
        super(EfilmError, self).__init__(message)
        self.status = status


class EfilmSession(object):
    """eFilm API session. The reader password is never persisted."""

    def __init__(self, addon):
        self.addon = addon
        self.profile = xbmcvfs.translatePath(addon.getAddonInfo("profile"))
        self.session_path = os.path.join(self.profile, "session.json")
        self.access_token = None
        self.localization = dict(DEFAULT_LOCALIZATION)

    def set_localization_from_headers(self, headers):
        if not isinstance(headers, dict):
            return
        self.localization = {
            "codeCountry": headers.get("cloudfront-viewer-country") or "ES",
            "city": headers.get("cloudfront-viewer-city") or headers.get("x-open-next-city") or "",
            "test": 2,
        }

    def has_session(self):
        return bool(self._load_refresh_token())

    def _load_refresh_token(self):
        try:
            with open(self.session_path, "r") as session_file:
                return json.load(session_file).get("refresh")
        except (IOError, ValueError, TypeError):
            return None

    def _load_session(self):
        try:
            with open(self.session_path, "r") as session_file:
                session = json.load(session_file)
                return session if isinstance(session, dict) else {}
        except (IOError, ValueError, TypeError):
            return {}

    def _save_session(self, refresh_token=None, loans=None):
        current = self._load_session()
        session = {
            "refresh": refresh_token or current.get("refresh"),
            "loans": current.get("loans", {}) if loans is None else loans,
        }
        os.makedirs(self.profile, mode=0o700, exist_ok=True)
        try:
            os.chmod(self.profile, 0o700)
        except OSError:
            pass
        descriptor = os.open(self.session_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(descriptor, "w") as session_file:
                json.dump(session, session_file)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise
        try:
            os.chmod(self.session_path, 0o600)
        except OSError:
            pass

    def clear(self):
        self.access_token = None
        try:
            os.remove(self.session_path)
        except OSError:
            pass

    def login(self, username, password):
        response = self._request(
            "POST",
            "auth/",
            {"id_client": EBIBLIOCAT_CLIENT_ID, "username": username, "password": password},
        )
        access = response.get("access")
        refresh = response.get("refresh")
        if not access or not refresh:
            raise EfilmError("eFilm did not return a valid sign-in session")
        self.access_token = access
        self._save_session(refresh, {})

    def visible_lists(self):
        entries = []
        page = 1
        while True:
            result = self._request(
                "GET", "products/visible-lists/?visible=true&page_size=100"
                "&elements_page_size=1&order_by=name,id&page=" + str(page)
            )
            entries.extend(result["results"])
            if not (result.get("links") or {}).get("next"):
                return entries
            page += 1

    def list_elements(self, list_id, page=1):
        return self._request(
            "GET", "products/lists/{}/elements-by-id/?page_size=24&page={}".format(
                int(list_id), int(page)
            )
        )

    def series(self, page=1):
        return self._request(
            "GET", "videos/series/?visible=true&page_size=24&page=" + str(int(page))
        )

    def series_detail(self, series_id):
        return self._request("GET", "products/collections/{}/".format(int(series_id)))

    def genres(self):
        return self._request("GET", "products/genres/audiovisual-available/")

    def movies(self, refresh=False):
        cache_path = os.path.join(self.profile, "movie-catalog.json")
        if not refresh:
            try:
                with open(cache_path, "r") as source:
                    cache = json.load(source)
                if time.time() - cache["updated"] < 21600:
                    return cache["products"]
            except (OSError, ValueError, KeyError, TypeError):
                pass

        def fetch(page):
            return self._request(
                "GET", "products/products/relevant/?skip_chapters=true&page_size=200"
                "&fields=id,name,slug,cover,genres,type,duration,year,description&page="
                + str(page)
            )

        first = fetch(1)
        products = list(first["results"])
        with ThreadPoolExecutor(max_workers=4) as executor:
            for result in executor.map(fetch, range(2, int(first["total_pages"]) + 1)):
                products.extend(result["results"])
        products = list({p["id"]: p for p in products}.values())
        os.makedirs(self.profile, mode=0o700, exist_ok=True)
        temporary = cache_path + "." + str(os.getpid()) + ".tmp"
        with open(temporary, "w") as target:
            json.dump({"updated": time.time(), "products": products}, target)
        os.replace(temporary, cache_path)
        return products

    def saved_loan(self, product_id):
        return self._load_session().get("loans", {}).get(str(product_id))

    def save_loan(self, product_id, loan_id):
        loans = self._load_session().get("loans", {})
        loans[str(product_id)] = loan_id
        self._save_session(loans=loans)

    def make_loan(self, product_id):
        result = self._authorized_request(
            "POST",
            "loans/loans/",
            {"product": int(product_id), "localization": self.localization},
        )
        loan = result.get("loan", result)
        if not loan.get("id"):
            raise EfilmError("eFilm did not return a loan for this title")
        return loan

    def get_playback(self, loan_id, language_id, subtitle_id):
        return self._authorized_request(
            "POST",
            "loans/displays/",
            {
                "loan": loan_id,
                "language": int(language_id),
                "subtitle": int(subtitle_id),
                "localization": self.localization,
            },
        )

    def _authorized_request(self, method, path, payload):
        if not self.access_token:
            self._refresh_access_token()
        try:
            return self._request(method, path, payload, self.access_token)
        except EfilmError as error:
            if error.status != 401:
                raise
            self.access_token = None
            self._refresh_access_token()
            return self._request(method, path, payload, self.access_token)

    def _refresh_access_token(self):
        refresh = self._load_refresh_token()
        if not refresh:
            raise EfilmError("Sign in to eFilm first")
        try:
            response = self._request("POST", "auth/refresh/", {"refresh": refresh})
        except EfilmError as error:
            if error.status in (400, 401):
                self.clear()
                raise EfilmError("Your eFilm session expired. Sign in again.", error.status)
            raise
        access = response.get("access")
        if not access:
            self.clear()
            raise EfilmError("eFilm did not refresh the sign-in session")
        self.access_token = access
        self._save_session(response.get("refresh") or refresh)

    def _request(self, method, path, payload=None, access_token=None):
        headers = {
            "Accept": "application/json",
            "Origin": "https://ebibliocat.efilm.info",
            "Accept-Language": LANGUAGE,
            "Content-Type": "application/json",
            "localization": json.dumps(self.localization, separators=(",", ":")),
        }
        if access_token:
            headers["Authorization"] = "JWT " + access_token
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(API_BASE + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
                if not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as error:
            try:
                body = json.loads(error.read().decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                body = {}
            if not isinstance(body, dict):
                body = {}
            message = body.get("detail") or body.get("msg") or "eFilm request failed"
            raise EfilmError(str(message), error.code)
        except (urllib.error.URLError, socket.timeout):
            raise EfilmError("Could not connect to eFilm")
        except (ValueError, UnicodeDecodeError):
            raise EfilmError("eFilm returned an unreadable response")
