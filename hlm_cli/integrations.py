import json
import urllib.request
import base64


INTEGRATIONS = []


def register(cls):
    INTEGRATIONS.append(cls())
    return cls


class Integration:
    type = None
    name = None

    def fetch(self, url, auth=None):
        return None


@register
class AdGuardHome(Integration):
    type = "adguard"
    name = "AdGuard Home"

    def fetch(self, url, auth=None):
        base = url.rstrip("/")
        try:
            req = urllib.request.Request(f"{base}/control/stats")
            if auth and auth.get("type") == "basic":
                creds = base64.b64encode(
                    f"{auth.get('username', '')}:{auth.get('password', '')}".encode()
                ).decode()
                req.add_header("Authorization", f"Basic {creds}")
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
