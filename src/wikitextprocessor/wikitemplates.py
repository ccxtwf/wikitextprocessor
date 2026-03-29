from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from .core import Wtp

MAX_WIKI_REQUEST_ATTEMPTS = 3

def _fetch_list_of_templates_and_modules(wtp: "Wtp") -> list[int]:
    import requests
    from .request_utils import get_user_agent

    results = []

    namespaces = [10, 828]
    exclude_suffixes = ["/doc", "/preload", "/testcases", ".css"]

    for ns in namespaces:
        apcontinue = ""
        while True:
            n_attempts = 0
            params = {
                "action": "query",
                "format": "json",
                "list": "allpages",
                "apnamespace": ns,
                "aplimit": "max",
                "apdir": "ascending",
                "apfilterredir": "nonredirects",
                "apcontinue": apcontinue
            }
            headers = {"user-agent": get_user_agent()}

            r = requests.get(
                wtp.api_entrypoint,
                params=params,
                headers=headers,
            )
            if r.ok:
                j = r.json()
                pages = j.get("query", {}).get("allpages", [])
                results.extend([page.get("pageid") for page in pages if not any(map(lambda suffix: page.get("title", "/doc").endswith(suffix), exclude_suffixes))])
                apcontinue = j.get("continue", {}).get("apcontinue", None)
                if apcontinue is None:
                    break
            else:
                n_attempts += 1
                wtp.error(f"Failed to connect to {r.url}, got status code {r.status_code} and response {r.text}")
                if n_attempts >= MAX_WIKI_REQUEST_ATTEMPTS:
                    raise Exception(f"Failed to fetch a response from the wiki after {n_attempts} attempts. Aborting...")

    return results

def _add_default_templates(wtp: "Wtp") -> None:
    ns = wtp.NAMESPACE_DATA["Template"]
    ns_id = ns["id"]
    ns_local_name = ns["name"]
    default_templates = {
        "!": "|",  # magic word
        "=": "=",
        "((": "&lbrace;&lbrace;",  # {{((}} -> {{
        "))": "&rbrace;&rbrace;",  # {{))}} -> }}
    }
    for title, body in default_templates.items():
        title = f"{ns_local_name}:{title}"
        if not wtp.page_exists(title, ns_id):
            wtp.add_page(title, ns_id, body)

def _map_mw_api_page_object_to_db_model(wtp: "Wtp", page):
    title, ns = page.get("title", None), page.get("ns", None)
    rev = page.get("revisions", [{}])[0]
    body = rev.get("*", None)
    if body is not None:
        body = wtp._template_to_body(str(title), body)
    contentmodel = rev.get("contentmodel", None)
    need_pre_expand = 0
    redirect_to = None
    return (title, ns, body, redirect_to, need_pre_expand, contentmodel)


def save_templates(wtp: "Wtp") -> None:
    import requests
    from .request_utils import get_user_agent
    from datetime import datetime
    from itertools import batched

    current_timestamp = datetime.now().isoformat()

    autocommit_mode = wtp.db_conn.autocommit
    wtp.db_conn.autocommit = False
    try:
        pageids = _fetch_list_of_templates_and_modules(wtp)
        for pid in batched(pageids, n=50):
            n_attempts = 0
            while n_attempts < MAX_WIKI_REQUEST_ATTEMPTS:
                params = {
                    "action": "query",
                    "format": "json",
                    "prop": "revisions",
                    "rvprop": "content",
                    "pageids": "|".join(map(str, pid)),
                }
                headers = {"user-agent": get_user_agent()}
                r = requests.get(
                    wtp.api_entrypoint,
                    params=params,
                    headers=headers,
                )
                if r.ok:
                    j = r.json()
                    pages = j.get("query", {}).get("pages", {}).values()
                    pages = [_map_mw_api_page_object_to_db_model(wtp, page) for page in pages]
                    wtp.db_conn.executemany(
                        """INSERT INTO pages (title, namespace_id, body,
                        redirect_to, need_pre_expand, model) VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(title, namespace_id) DO UPDATE SET
                        body=excluded.body, redirect_to=excluded.redirect_to,
                        need_pre_expand=excluded.need_pre_expand, model=excluded.model""",
                        pages,
                    )
                    break
                else:
                    n_attempts += 1
                    wtp.error(f"Failed to connect to {r.url}, got status code {r.status_code} and response {r.text}")
                    if n_attempts >= MAX_WIKI_REQUEST_ATTEMPTS:
                        raise Exception(f"Failed to fetch a response from the wiki after {n_attempts} attempts. Aborting...")
        _add_default_templates(wtp)
        wtp.db_conn.execute(
            "DELETE FROM last_saved;"
        )
        wtp.db_conn.execute(
            "INSERT INTO last_saved (timestamp) VALUES (?);",
            (current_timestamp, )
        )
        wtp.db_conn.commit()
        wtp.note("Repopulated template store.")
    except Exception as err:
        wtp.error(str(err))
        wtp.db_conn.rollback()
        wtp.db_conn.autocommit = autocommit_mode
