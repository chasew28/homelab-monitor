import json
import urllib.request
import base64
import xml.etree.ElementTree as ET


INTEGRATIONS = []


def register(cls):
    INTEGRATIONS.append(cls())
    return cls


class Integration:
    type = None
    name = None

    def fetch(self, url, auth=None):
        return None


def _basic_auth(req, auth):
    if auth and auth.get("type") == "basic":
        creds = base64.b64encode(
            f"{auth.get('username', '')}:{auth.get('password', '')}".encode()
        ).decode()
        req.add_header("Authorization", f"Basic {creds}")


def _token_auth(req, auth):
    if auth and auth.get("type") == "token":
        req.add_header("X-Plex-Token", auth.get("token", ""))


@register
class AdGuardHome(Integration):
    type = "adguard"
    name = "AdGuard Home"

    def fetch(self, url, auth=None):
        base = url.rstrip("/")
        try:
            req = urllib.request.Request(f"{base}/control/stats")
            _basic_auth(req, auth)
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode())
            queries = data.get("num_dns_queries", 0)
            blocked = data.get("num_blocked_filtering", 0)
            return {
                "type": self.type,
                "name": self.name,
                "stats": {
                    "queries": queries,
                    "blocked": blocked,
                    "blockedPercent": round(blocked / max(queries, 1) * 100, 1),
                },
            }
        except urllib.request.HTTPError as e:
            if e.code == 401:
                return {"type": self.type, "name": self.name, "authError": True}
            return None
        except Exception:
            return None


@register
class PiHole(Integration):
    type = "pihole"
    name = "Pi-hole"

    def fetch(self, url, auth=None):
        base = url.rstrip("/")
        try:
            api_url = f"{base}/admin/api.php?summary"
            req = urllib.request.Request(api_url)
            _basic_auth(req, auth)
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode())
            queries = int(data.get("dns_queries_today", 0))
            blocked = int(data.get("ads_blocked_today", 0))
            return {
                "type": self.type,
                "name": self.name,
                "stats": {
                    "queries": queries,
                    "blocked": blocked,
                    "blockedPercent": round(blocked / max(queries, 1) * 100, 1),
                },
            }
        except urllib.request.HTTPError as e:
            if e.code == 401:
                return {"type": self.type, "name": self.name, "authError": True}
            return None
        except Exception:
            return None


@register
class Plex(Integration):
    type = "plex"
    name = "Plex"

    def fetch(self, url, auth=None):
        base = url.rstrip("/")
        try:
            req = urllib.request.Request(f"{base}/status/sessions")
            _token_auth(req, auth)
            resp = urllib.request.urlopen(req, timeout=5)
            root = ET.fromstring(resp.read())
            sessions = int(root.get("size", 0))
            return {
                "type": self.type,
                "name": self.name,
                "stats": {
                    "sessions": sessions,
                },
            }
        except urllib.request.HTTPError as e:
            if e.code == 401:
                return {"type": self.type, "name": self.name, "authError": True}
            return None
        except Exception:
            return None


@register
class QBittorrent(Integration):
    type = "qbittorrent"
    name = "qBittorrent"

    def fetch(self, url, auth=None):
        base = url.rstrip("/")
        try:
            req = urllib.request.Request(f"{base}/api/v2/transfer/info")
            _basic_auth(req, auth)
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read().decode())
            dl = data.get("dl_speed", 0)
            up = data.get("up_speed", 0)
            return {
                "type": self.type,
                "name": self.name,
                "stats": {
                    "dl_speed": dl,
                    "up_speed": up,
                },
            }
        except urllib.request.HTTPError as e:
            if e.code == 401:
                return {"type": self.type, "name": self.name, "authError": True}
            return None
        except Exception:
            return None
