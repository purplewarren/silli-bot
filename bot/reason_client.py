import os, json, logging, time, math
from typing import Any, Dict, Optional
import requests

log = logging.getLogger("silli.reasoner")

def _normalize_base(base: str) -> str:
    return (base or "").rstrip("/")

class ReasonClient:
    def __init__(self):
        self.base = _normalize_base(os.getenv("REASONER_BASE_URL", ""))
        self.token = os.getenv("REASONER_TOKEN", "")
        self.timeout = int(os.getenv("REASONER_TIMEOUT", "30"))
        self.session = requests.Session()
        self.session.headers.update({
            "X-Reasoner-Token": self.token,
            "Content-Type": "application/json",
        })
        # Circuit breaker fields
        self.fail_count = 0
        self.opened_until = 0.0
        if not self.base or not self.token:
            log.warning("Reasoner not configured: base=%r token=%s",
                        self.base, "SET" if self.token else "MISSING")

    def _url(self, path: str) -> str:
        return f"{self.base}{path if path.startswith('/') else '/'+path}"

    def _circuit_open(self) -> bool:
        return time.time() < self.opened_until

    def _record_success(self):
        self.fail_count = 0

    def _record_failure(self):
        self.fail_count += 1
        if self.fail_count >= 3:
            self.opened_until = time.time() + 60

    def health(self) -> Dict[str, Any]:
        try:
            r = self.session.get(self._url("/health"), timeout=self.timeout)
            return r.json()
        except Exception as e:
            log.exception("reasoner.health failed: %s", e)
            return {"status":"error","error":str(e)}

    def status(self) -> Dict[str, Any]:
        try:
            r = self.session.get(self._url("/status"), timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.exception("reasoner.status failed: %s", e)
            return {"status":"error","error":str(e)}

    def reason(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Returns dict with either tips/rationale/model_used or error."""
        if self._circuit_open():
            return {"error":"unavailable","details":"circuit_open"}
        
        url = self._url("/v1/reason")
        body = json.dumps(payload)
        
        for attempt in range(2):
            try:
                tmo = self.timeout if attempt == 0 else math.ceil(self.timeout * 1.5)
                if attempt:
                    time.sleep(0.5)
                
                log.debug("reasoner.request attempt=%s url=%s timeout=%s body=%s", attempt+1, url, tmo, body)
                r = self.session.post(url, data=body, timeout=tmo)
                log.debug("reasoner.response status=%s body=%s", r.status_code, r.text[:800])
                r.raise_for_status()
                self._record_success()
                return r.json()
                
            except (requests.Timeout, requests.HTTPError, requests.ConnectionError) as e:
                log.warning("reasoner attempt %s failed: %s", attempt+1, e)
                self._record_failure()
            except Exception as e:
                log.exception("reasoner fatal")
                self._record_failure()
                break
        
        return {"error":"failed_after_retries","details":f"fail_count={self.fail_count}"}

# Singleton
client = ReasonClient()