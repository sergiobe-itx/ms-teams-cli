#!/usr/bin/env python3
from __future__ import annotations
"""
teams.py — Read Microsoft Teams channels AND chats (group, 1:1, meetings).

Two auth paths:
  1. Graph API (channels): token via `az account get-access-token --resource https://graph.microsoft.com`
  2. Skype/Chat API (chats): token via `az account get-access-token --resource https://chatsvcagg.teams.microsoft.com`
     then exchanged at https://authsvc.teams.microsoft.com/v1.0/authz for a skypeToken.

Both tokens are cached and auto-renewed. No manual export needed.

Usage:
    python3 teams.py <command> [options]
    python3 teams.py help
"""

import argparse
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── SSL fix for macOS ─────────────────────────────────────────────────────────
# Homebrew Python on macOS often can't find the system cert bundle.
# Set SSL_CERT_FILE to the system cert if not already set.

if sys.platform == "darwin" and "SSL_CERT_FILE" not in os.environ:
    for cert_path in ["/etc/ssl/cert.pem", "/usr/local/etc/openssl/cert.pem"]:
        if os.path.exists(cert_path):
            os.environ["SSL_CERT_FILE"] = cert_path
            break

# ── Constants ──────────────────────────────────────────────────────────────────

GRAPH = "https://graph.microsoft.com/v1.0"
GRAPH_BETA = "https://graph.microsoft.com/beta"
TOKEN_CACHE = Path(
    os.environ.get("TEAMS_TOKEN_CACHE", Path.home() / ".cache" / "teams-token.json")
)
SKYPE_TOKEN_CACHE = Path(
    os.environ.get(
        "TEAMS_SKYPE_TOKEN_CACHE", Path.home() / ".cache" / "teams-skype-token.json"
    )
)
TOKEN_MARGIN = 300  # seconds before expiry to proactively renew

# ── Token management ───────────────────────────────────────────────────────────


def _load_cache() -> tuple[str, int]:
    """Return (token, expires_timestamp) from cache, or ('', 0) on miss/error."""
    try:
        d = json.loads(TOKEN_CACHE.read_text())
        token = d.get("token", "")
        expires_on = d.get("expiresOn", "")
        if not token or not expires_on:
            return "", 0
        exp_ts = int(
            datetime.fromisoformat(expires_on.replace("Z", "+00:00")).timestamp()
        )
        return token, exp_ts
    except Exception:
        return "", 0


def _renew_token() -> str:
    """Acquire a fresh token via `az` and persist to cache. Returns token string."""
    result = subprocess.run(
        [
            "az",
            "account",
            "get-access-token",
            "--resource",
            "https://graph.microsoft.com",
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr or "")
        die("az login required. Run: az login")

    d = json.loads(result.stdout)
    token = d["accessToken"]
    expires_on = d["expiresOn"]
    # Normalise az format "YYYY-MM-DD HH:MM:SS.ffffff" → "YYYY-MM-DDTHH:MM:SSZ"
    expires_on = re.sub(r"\.\d+$", "", expires_on.replace(" ", "T")) + "Z"

    TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE.write_text(json.dumps({"token": token, "expiresOn": expires_on}))
    sys.stderr.write(f"  [token] Renovado, expira: {expires_on}\n")
    return token


def get_token() -> str:
    """Return a valid token, renewing only when expired (or within TOKEN_MARGIN seconds)."""
    now = int(datetime.now(timezone.utc).timestamp())
    token, exp_ts = _load_cache()
    if token and exp_ts > now + TOKEN_MARGIN:
        return token
    return _renew_token()


# ── Skype token management (for chats) ────────────────────────────────────────


def _load_skype_cache() -> tuple[str, str, int]:
    """Return (skype_token, chat_service_url, expires_timestamp) from cache."""
    try:
        d = json.loads(SKYPE_TOKEN_CACHE.read_text())
        skype_token = d.get("skypeToken", "")
        chat_service = d.get("chatService", "")
        exp_ts = d.get("expiresAt", 0)
        if not skype_token or not chat_service:
            return "", "", 0
        return skype_token, chat_service, exp_ts
    except Exception:
        return "", "", 0


def _renew_skype_token() -> tuple[str, str]:
    """
    Acquire a fresh Skype token:
    1. Get AAD token for chatsvcagg.teams.microsoft.com via `az`
    2. Exchange it at authsvc.teams.microsoft.com for a skypeToken
    Returns (skype_token, chat_service_url).
    """
    # Step 1: AAD token for Skype API
    result = subprocess.run(
        [
            "az",
            "account",
            "get-access-token",
            "--resource",
            "https://api.spaces.skype.com",
            "-o",
            "json",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr or "")
        die("az login required. Run: az login")

    aad_token = json.loads(result.stdout)["accessToken"]

    # Step 2: Exchange for Skype token
    authz_url = "https://authsvc.teams.microsoft.com/v1.0/authz"
    body = json.dumps({"resourceUrl": "https://api.spaces.skype.com"}).encode()
    req = urllib.request.Request(
        authz_url,
        data=body,
        headers={
            "Authorization": f"Bearer {aad_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            authz = json.loads(r.read())
    except Exception as exc:
        die(f"Skype token exchange failed: {exc}")

    skype_token = authz["tokens"]["skypeToken"]
    expires_in = authz["tokens"].get("expiresIn", 3600)
    chat_service = authz.get("regionGtms", {}).get(
        "chatService", "https://emea.ng.msg.teams.microsoft.com"
    )

    # Cache it
    now = int(datetime.now(timezone.utc).timestamp())
    SKYPE_TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    SKYPE_TOKEN_CACHE.write_text(
        json.dumps(
            {
                "skypeToken": skype_token,
                "chatService": chat_service,
                "expiresAt": now + expires_in,
            }
        )
    )
    exp_dt = datetime.fromtimestamp(now + expires_in, tz=timezone.utc).isoformat()
    sys.stderr.write(f"  [skype-token] Renewed, expires: {exp_dt}\n")
    return skype_token, chat_service


def get_skype_token() -> tuple[str, str]:
    """Return (skype_token, chat_service_url), renewing if needed."""
    now = int(datetime.now(timezone.utc).timestamp())
    skype_token, chat_service, exp_ts = _load_skype_cache()
    if skype_token and exp_ts > now + TOKEN_MARGIN:
        return skype_token, chat_service
    return _renew_skype_token()


# ── HTTP helpers ───────────────────────────────────────────────────────────────


def _request(url: str, retry: bool = True) -> dict:
    """GET url with current token. Auto-retries once on 401."""
    token = get_token()
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 401 and retry:
            sys.stderr.write("  [token] 401 recibido, renovando...\n")
            _renew_token()
            return _request(url, retry=False)
        body = ""
        try:
            body = json.loads(e.read()).get("error", {}).get("message", "")[:120]
        except Exception:
            pass
        die(f"Graph API HTTP {e.code} — {body}\n  URL: {url}")
    except Exception as exc:
        die(f"Request failed: {exc}\n  URL: {url}")


def _skype_request(url: str, retry: bool = True) -> dict:
    """GET url with Skype token. Auto-retries once on 401/403."""
    skype_token, _ = get_skype_token()
    req = urllib.request.Request(
        url,
        headers={
            "Authentication": f"skypetoken={skype_token}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403) and retry:
            sys.stderr.write(f"  [skype-token] {e.code} received, renewing...\n")
            _renew_skype_token()
            return _skype_request(url, retry=False)
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        die(f"Chat API HTTP {e.code} — {body}\n  URL: {url}")
    except Exception as exc:
        die(f"Chat request failed: {exc}\n  URL: {url}")


def _skype_post(url: str, body: dict, retry: bool = True) -> dict:
    """POST to Skype/Chat API with Skype token. Auto-retries once on 401/403."""
    skype_token, _ = get_skype_token()
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authentication": f"skypetoken={skype_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp_body = r.read()
            return json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        if e.code in (401, 403) and retry:
            sys.stderr.write(f"  [skype-token] {e.code} received, renewing...\n")
            _renew_skype_token()
            return _skype_post(url, body, retry=False)
        resp = ""
        try:
            resp = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        die(f"Chat API POST HTTP {e.code} — {resp}\n  URL: {url}")
    except Exception as exc:
        die(f"Chat POST failed: {exc}\n  URL: {url}")


def paginate(url: str, max_pages: int = 1, stop_before: str = "2000-01-01") -> list:
    """
    Follow @odata.nextLink up to max_pages times.
    Stops early when the oldest item on a page has createdDateTime < stop_before.
    Returns merged list of all .value[] items.
    """
    items, page, next_url = [], 0, url
    while next_url and page < max_pages:
        data = _request(next_url)
        vals = data.get("value", [])
        items.extend(vals)
        page += 1
        next_url = data.get("@odata.nextLink", "")
        dates = [m.get("createdDateTime", "") for m in vals if m.get("createdDateTime")]
        if dates and min(dates)[:10] < stop_before:
            break
    return items


# ── Text helpers ───────────────────────────────────────────────────────────────


def clean(html: str) -> str:
    """Strip HTML tags and decode common entities."""
    if not html:
        return ""
    t = re.sub(r"<[^>]+>", "", html)
    for entity, char in [
        ("&nbsp;", " "),
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&apos;", "'"),
        ("&quot;", '"'),
        ("&#39;", "'"),
    ]:
        t = t.replace(entity, char)
    return re.sub(r"\s+", " ", t).strip()


def author(msg: dict) -> str:
    return str(
        ((msg.get("from") or {}).get("user") or {}).get("displayName") or "(bot)"
    )


def fmt_dt(iso: str, length: int = 16) -> str:
    return iso[:length].replace("T", " ")


def die(msg: str) -> None:
    sys.stderr.write(f"ERROR: {msg}\n")
    sys.exit(1)


def parse_teams_url(url: str) -> dict:
    """Extract team_id, channel_id, message_id, tenant_id from any Teams URL."""
    parsed = urllib.parse.urlparse(url)
    params = dict(urllib.parse.parse_qsl(parsed.query))
    path = urllib.parse.unquote(parsed.path)

    team_id = params.get("groupId", "")
    tenant_id = params.get("tenantId", "")
    channel_id = ""
    message_id = ""

    m = re.search(r"/l/message/([^/]+)/([^/?]+)", path)
    if m:
        channel_id = urllib.parse.unquote(m.group(1))
        message_id = urllib.parse.unquote(m.group(2))

    if not channel_id:
        m = re.search(r"/l/channel/([^/]+)", path)
        if m:
            channel_id = urllib.parse.unquote(m.group(1))

    if not channel_id:
        m = re.search(r"/l/team/([^/]+)", path)
        if m:
            channel_id = urllib.parse.unquote(m.group(1))

    return {
        "team_id": team_id,
        "channel_id": channel_id,
        "message_id": message_id,
        "tenant_id": tenant_id,
    }


# ── Commands ───────────────────────────────────────────────────────────────────


def cmd_token(args):
    """Force token renewal and show expiry."""
    _renew_token()
    d = json.loads(TOKEN_CACHE.read_text())
    print(f"Token OK, expira: {d['expiresOn']}")


def cmd_parse_url(args):
    """Parse a Teams URL and print extracted IDs + ready-to-use commands."""
    url = args.url or input("Teams URL: ").strip()
    ids = parse_teams_url(url)

    print(f"TEAM_ID    : {ids['team_id'] or '(not found)'}")
    print(f"CHANNEL_ID : {ids['channel_id'] or '(not found)'}")
    print(f"MESSAGE_ID : {ids['message_id'] or '(not found)'}")
    print(f"TENANT_ID  : {ids['tenant_id'] or '(not found)'}")

    if ids["team_id"]:
        print()
        print(f"python3 teams.py channels --team {ids['team_id']}")
    if ids["team_id"] and ids["channel_id"]:
        print(
            f"python3 teams.py messages --team {ids['team_id']} --channel {ids['channel_id']}"
        )
    if ids["team_id"] and ids["channel_id"] and ids["message_id"]:
        print(
            f"python3 teams.py replies  --team {ids['team_id']} --channel {ids['channel_id']} --thread {ids['message_id']}"
        )


def cmd_teams(args):
    """List all teams the user belongs to."""
    data = _request(f"{GRAPH}/me/joinedTeams?$select=id,displayName,description")
    teams = data.get("value", [])

    if args.json:
        print(json.dumps(teams, indent=2, ensure_ascii=False))
        return

    print(f"{'TEAM':<45} {'ID':<38}")
    print("-" * 84)
    for t in teams:
        print(f"{t['displayName']:<45} {t['id']:<38}")
    print(f"\n{len(teams)} teams.")


def cmd_channels(args):
    """List channels in a team."""
    if not args.team:
        die("--team required")
    data = _request(
        f"{GRAPH}/teams/{args.team}/channels?$select=id,displayName,description"
    )
    channels = data.get("value", [])

    if args.json:
        print(json.dumps(channels, indent=2, ensure_ascii=False))
        return

    print(f"{'CHANNEL':<45} {'ID':<60}")
    print("-" * 106)
    for c in channels:
        print(f"{c['displayName']:<45} {c['id']:<60}")
    print(f"\n{len(channels)} channels.")


def cmd_messages(args):
    """List messages in a channel, with optional pagination."""
    if not args.team or not args.channel:
        die("--team and --channel required")

    url = f"{GRAPH_BETA}/teams/{args.team}/channels/{args.channel}/messages?$top={args.top}"
    if args.since:
        url += f"&$filter=createdDateTime%20ge%20{args.since}"

    msgs = paginate(url, max_pages=args.pages)

    if args.json:
        print(json.dumps(msgs, indent=2, ensure_ascii=False))
        return

    print(f"{'AUTHOR':<25} {'WHEN':<20} {'REPLIES':<8} SUBJECT / PREVIEW")
    print("-" * 100)
    for m in msgs:
        if m.get("messageType") != "message":
            continue
        rc = "(reply)" if m.get("replyToId") else str(m.get("replyCount") or "-")
        body = clean(m.get("body", {}).get("content", ""))[:80]
        print(
            f"{author(m):<25} {fmt_dt(m.get('createdDateTime', '')):<20} {rc:<8} {body}"
        )
    print(f"\n{len(msgs)} messages.")


def cmd_replies(args):
    """Show a thread: original post + all replies."""
    if not args.team or not args.channel or not args.thread:
        die("--team, --channel and --thread required")

    base = f"{GRAPH_BETA}/teams/{args.team}/channels/{args.channel}/messages"
    parent = _request(f"{base}/{args.thread}")
    data = _request(f"{base}/{args.thread}/replies?$top={args.top}")
    replies = data.get("value", [])

    if args.json:
        print(
            json.dumps(
                {"parent": parent, "replies": replies}, indent=2, ensure_ascii=False
            )
        )
        return

    print("── ORIGINAL POST " + "─" * 44)
    print(f"From : {author(parent)}")
    print(f"Date : {fmt_dt(parent.get('createdDateTime', ''))}")
    print(f"Body : {clean(parent.get('body', {}).get('content', ''))[:300]}")
    print()
    print(f"── REPLIES ({args.top} max) " + "─" * 40)
    if not replies:
        print("  (no replies)")
    for i, m in enumerate(replies, 1):
        print(f"[{i}] {author(m)} @ {fmt_dt(m.get('createdDateTime', ''))}")
        print(f"    {clean(m.get('body', {}).get('content', ''))[:200]}")
        print()
    print(f"{len(replies)} replies.")


def cmd_unanswered(args):
    """List posts with no replies within the last N minutes."""
    if not args.team or not args.channel:
        die("--team and --channel required")

    data = _request(
        f"{GRAPH_BETA}/teams/{args.team}/channels/{args.channel}/messages?$top=50"
    )
    msgs = data.get("value", [])
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=args.minutes)

    print(f"Posts without replies in last {args.minutes} min:")
    print(f"{'AUTHOR':<25} {'WHEN':<20} PREVIEW")
    print("-" * 90)

    found = 0
    for m in msgs:
        if m.get("messageType") != "message":
            continue
        if m.get("replyToId"):
            continue
        if m.get("deletedDateTime"):
            continue
        if (m.get("replyCount") or 0) > 0:
            continue
        try:
            created = datetime.fromisoformat(
                re.sub(r"\.\d+", "", m["createdDateTime"]).replace("Z", "+00:00")
            )
        except Exception:
            continue
        if created < cutoff:
            continue
        body = clean(m.get("body", {}).get("content", ""))[:60]
        print(f"{author(m):<25} {fmt_dt(m.get('createdDateTime', '')):<20} {body}")
        found += 1

    print(f"\n{found} unanswered posts (window: last {args.minutes} min).")


def cmd_scan(args):
    """
    Scan all channels of a team for activity on a specific date.
    Fetches thread roots + replies, filtering for activity on --date.
    """
    if not args.team:
        die("--team required")
    if not args.date:
        die("--date YYYY-MM-DD required")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        die("--date must be YYYY-MM-DD")

    target = args.date
    stop_before = (datetime.strptime(target, "%Y-%m-%d") - timedelta(days=3)).strftime(
        "%Y-%m-%d"
    )

    # Fetch channel list
    ch_data = _request(f"{GRAPH}/teams/{args.team}/channels?$select=id,displayName")
    channels = ch_data.get("value", [])

    print(
        f"Scanning {len(channels)} channels for activity on {target} "
        f"(pages/channel: {args.pages})...\n"
    )

    total_posts = 0
    total_replies = 0
    active_channels = 0

    for ch in channels:
        cid = ch["id"]
        cname = ch["displayName"]
        sys.stderr.write(f"  → {cname}\n")
        sys.stderr.flush()

        # Paginate messages
        url = f"{GRAPH_BETA}/teams/{args.team}/channels/{cid}/messages?$top={args.top}"
        msgs = paginate(url, max_pages=args.pages, stop_before=stop_before)

        # Collect thread roots created from stop_before onwards
        roots = {
            m["id"]: m
            for m in msgs
            if m.get("messageType") == "message"
            and not m.get("deletedDateTime")
            and not m.get("replyToId")
            and m.get("createdDateTime", "")[:10] >= stop_before
        }

        if not roots:
            continue

        channel_threads = []
        for mid, root in sorted(
            roots.items(), key=lambda x: x[1].get("createdDateTime", "")
        ):
            root_dt = root.get("createdDateTime", "")
            root_on_day = root_dt.startswith(target)

            # Fetch replies and filter for target date
            rep_data = _request(
                f"{GRAPH_BETA}/teams/{args.team}/channels/{cid}"
                f"/messages/{mid}/replies?$top=50"
            )
            day_replies = [
                r
                for r in rep_data.get("value", [])
                if r.get("createdDateTime", "").startswith(target)
                and not r.get("deletedDateTime")
            ]

            if not root_on_day and not day_replies:
                continue

            channel_threads.append(
                {
                    "root_dt": fmt_dt(root_dt),
                    "root_author": author(root),
                    "root_body": clean(root.get("body", {}).get("content", ""))[:120],
                    "root_on_day": root_on_day,
                    "replies": [
                        {
                            "time": r["createdDateTime"][11:16],
                            "author": author(r),
                            "body": clean(r.get("body", {}).get("content", ""))[:100],
                        }
                        for r in sorted(
                            day_replies, key=lambda x: x.get("createdDateTime", "")
                        )
                    ],
                }
            )

        if not channel_threads:
            continue

        day_posts = sum(1 for t in channel_threads if t["root_on_day"])
        day_reps = sum(len(t["replies"]) for t in channel_threads)
        total_posts += day_posts
        total_replies += day_reps
        active_channels += 1

        print("━" * 64)
        print(f"  {cname}  [{day_posts} posts | {day_reps} replies]")
        print("━" * 64)

        for t in channel_threads:
            tag = " ◀ HOY" if t["root_on_day"] else f"  (hilo del {t['root_dt'][:10]})"
            print(f"  ▶ [{t['root_dt']}]{tag}")
            print(f"     {t['root_author']}: {t['root_body']}")
            for r in t["replies"]:
                print(f"    ↩ {r['time']}  {r['author']:<28} {r['body']}")
            print()

    print("=" * 64)
    print(f"TOTAL {target}: {total_posts} posts nuevos | {total_replies} replies")
    print(f"Canales activos: {active_channels}/{len(channels)}")


# ── Chat helpers ───────────────────────────────────────────────────────────────


def _classify_chat(conv_id: str) -> str:
    """Classify a conversation by its ID pattern.

    Known 1:1 ID formats:
      - 19:<uuid>_<uuid>@unq.gbl.spaces  (modern Teams)
      - 8:orgid:<hex>                      (legacy Skype-interop)
      - contains ':8:' or ':orgid:'        (other legacy formats)

    Known group formats:
      - @thread.v2, @thread.tacv2          (modern group chats)
      - @thread.skype with a topic         (legacy group chats — classified below by caller)

    Note: @thread.skype WITHOUT a topic may be either a legacy 1:1 or a group.
    We classify those as 'other' and let the caller disambiguate if needed.
    """
    if ":meeting_" in conv_id:
        return "meeting"
    if "thread.v2" in conv_id or "thread.tacv2" in conv_id:
        return "group"
    if "@unq.gbl.spaces" in conv_id:
        return "1:1"
    if ":8:" in conv_id or ":orgid:" in conv_id:
        return "1:1"
    return "other"


def _chat_display_name(conv: dict) -> str:
    """Best-effort display name for a chat conversation.

    For 1:1 chats, the last message sender may be the current user, making
    imdisplayname useless for identifying the *other* person. In that case,
    we fall back to fetching a small batch of recent messages to find a
    different sender name.
    """
    # threadProperties.topic for group chats / meetings
    topic = (conv.get("threadProperties") or {}).get("topic", "")
    if topic:
        return topic

    # For 1:1, use the other person's display name from lastMessage sender
    last_msg = conv.get("lastMessage") or {}
    sender = last_msg.get("imdisplayname", "")

    # Detect if the sender is the current user (i.e. we sent the last message)
    # by comparing with fromDisplayNameInToken which is always the current user's name
    my_name = last_msg.get("fromDisplayNameInToken", "")
    is_my_own_msg = sender and my_name and sender == my_name

    if sender and not is_my_own_msg:
        return f"Chat with {sender}"

    # If we sent the last message (or no sender), try to resolve the other
    # person by fetching recent messages from the conversation
    conv_id = conv.get("id", "")
    is_one_to_one = (
        _classify_chat(conv_id) == "1:1"
        or (conv.get("threadProperties") or {}).get("productThreadType") == "OneToOneChat"
    )
    if is_one_to_one and conv_id:
        other = _resolve_other_person(conv_id, my_name)
        if other:
            return f"Chat with {other}"

    if sender:
        return f"Chat with {sender}"

    return conv.get("id", "(unknown)")[:40]


def _resolve_other_person(conv_id: str, my_name: str) -> str:
    """Fetch recent messages from a 1:1 chat to find the other person's name.

    Looks for a message with imdisplayname different from the current user.
    Returns the other person's display name or empty string.
    """
    try:
        _, chat_service = get_skype_token()
        url = f"{chat_service}/v1/users/ME/conversations/{conv_id}/messages?pageSize=10"
        data = _skype_request(url)
        for msg in data.get("messages", []):
            name = msg.get("imdisplayname", "")
            if name and name != my_name:
                return name
    except Exception:
        pass
    return ""


def _is_unread(conv: dict) -> bool:
    """
    Determine if a conversation has unread messages.
    consumptionhorizon format: "timestamp1;timestamp2;timestamp3"
    Compare first value against lastMessage.id (which is a timestamp-based ID).
    If lastMessage.id > first value of consumptionhorizon → unread.
    If consumptionhorizon is missing → treat as unread.
    """
    props = conv.get("properties") or {}
    horizon = props.get("consumptionhorizon", "")
    last_msg = conv.get("lastMessage") or {}
    last_id = last_msg.get("id", "")

    if not last_id:
        return False  # No messages at all

    if not horizon:
        return True  # Never opened → unread

    try:
        horizon_ts = horizon.split(";")[0]
        return int(last_id) > int(horizon_ts)
    except (ValueError, IndexError):
        return True  # Can't parse → assume unread


def _fmt_chat_time(iso_or_ts: str) -> str:
    """Format a Teams chat timestamp (ISO or epoch-based) for display."""
    if not iso_or_ts:
        return ""
    # composetime is ISO format like "2026-03-28T10:30:00.000Z"
    return iso_or_ts[:16].replace("T", " ")


# ── Chat commands ──────────────────────────────────────────────────────────────


def cmd_chats(args):
    """List all chats (group, 1:1, meetings) via Skype/Chat API."""
    _, chat_service = get_skype_token()
    page_size = args.top or 50
    url = f"{chat_service}/v1/users/ME/conversations?view=mychats&pageSize={page_size}"
    data = _skype_request(url)
    conversations = data.get("conversations", [])

    # Filter by type if requested
    if args.type:
        conversations = [c for c in conversations if _classify_chat(c.get("id", "")) == args.type]

    if args.json:
        print(json.dumps(conversations, indent=2, ensure_ascii=False))
        return

    print(f"{'TYPE':<10} {'NAME':<50} {'LAST MESSAGE':<20} PREVIEW")
    print("-" * 120)
    for conv in conversations:
        ctype = _classify_chat(conv.get("id", ""))
        name = _chat_display_name(conv)[:48]
        last_msg = conv.get("lastMessage") or {}
        when = _fmt_chat_time(last_msg.get("composetime", ""))
        preview = clean(last_msg.get("content", ""))[:40]
        sender = last_msg.get("imdisplayname", "")
        if sender and preview:
            preview = f"{sender}: {preview}"
        elif sender:
            preview = sender
        print(f"{ctype:<10} {name:<50} {when:<20} {preview[:50]}")

    print(f"\n{len(conversations)} conversations.")


def cmd_unread(args):
    """List chats with unread messages."""
    _, chat_service = get_skype_token()
    url = f"{chat_service}/v1/users/ME/conversations?view=mychats&pageSize=200"
    data = _skype_request(url)
    conversations = data.get("conversations", [])

    unread = [c for c in conversations if _is_unread(c)]

    # Filter by type if requested
    if args.type:
        unread = [c for c in unread if _classify_chat(c.get("id", "")) == args.type]

    if args.json:
        print(json.dumps(unread, indent=2, ensure_ascii=False))
        return

    print(f"{'TYPE':<10} {'NAME':<50} {'WHEN':<20} LAST MESSAGE")
    print("-" * 120)
    for conv in unread:
        ctype = _classify_chat(conv.get("id", ""))
        name = _chat_display_name(conv)[:48]
        last_msg = conv.get("lastMessage") or {}
        when = _fmt_chat_time(last_msg.get("composetime", ""))
        sender = last_msg.get("imdisplayname", "")
        preview = clean(last_msg.get("content", ""))[:50]
        if sender and preview:
            preview = f"{sender}: {preview}"
        elif sender:
            preview = sender
        print(f"{ctype:<10} {name:<50} {when:<20} {preview[:50]}")

    print(f"\n{len(unread)} unread conversations (of {len(conversations)} total).")


def cmd_chat_messages(args):
    """Read messages from a specific chat conversation."""
    if not args.chat:
        die("--chat required (conversation ID)")

    _, chat_service = get_skype_token()
    page_size = args.top or 30
    url = f"{chat_service}/v1/users/ME/conversations/{args.chat}/messages?pageSize={page_size}"
    data = _skype_request(url)
    messages = data.get("messages", [])

    # Filter to actual messages (not system/control)
    user_msgs = [
        m
        for m in messages
        if m.get("messagetype") in ("Text", "RichText", "RichText/Html")
    ]

    if args.json:
        print(json.dumps(user_msgs, indent=2, ensure_ascii=False))
        return

    # Print in chronological order (API returns newest first)
    user_msgs.reverse()

    print(f"{'WHEN':<20} {'FROM':<30} MESSAGE")
    print("-" * 100)
    for m in user_msgs:
        when = _fmt_chat_time(m.get("composetime", ""))
        sender = m.get("imdisplayname", "(unknown)")
        body = clean(m.get("content", ""))[:120]
        print(f"{when:<20} {sender:<30} {body}")

    print(f"\n{len(user_msgs)} messages.")


def cmd_send_message(args):
    """Send a message to a chat conversation. Requires explicit confirmation."""
    if not args.chat:
        die("--chat required (conversation ID)")
    if not args.message:
        die("--message required (text to send)")

    _, chat_service = get_skype_token()

    # Resolve chat name for display
    chat_name = args.chat
    try:
        conv_url = f"{chat_service}/v1/users/ME/conversations?view=mychats&pageSize=200"
        conv_data = _skype_request(conv_url)
        for c in conv_data.get("conversations", []):
            if c.get("id") == args.chat:
                chat_name = _chat_display_name(c)
                break
    except Exception:
        pass  # Fall back to raw ID

    # Show what will be sent and ask for confirmation
    print("=" * 60)
    print(f"  TO:      {chat_name}")
    print(f"  CHAT ID: {args.chat}")
    print(f"  MESSAGE: {args.message}")
    print("=" * 60)

    if args.yes:
        confirm = "y"
    else:
        sys.stdout.write("\nSend this message? [y/N] ")
        sys.stdout.flush()
        confirm = input().strip().lower()

    if confirm != "y":
        print("Cancelled — message NOT sent.")
        return

    # Send the message — always prefix with robot emoji to identify agent messages
    message = args.message if args.message.startswith("🤖") else f"🤖 {args.message}"
    url = f"{chat_service}/v1/users/ME/conversations/{args.chat}/messages"
    body = {
        "content": message,
        "messagetype": "RichText/Html" if "<" in args.message else "Text",
        "contenttype": "text",
    }
    result = _skype_post(url, body)

    msg_id = result.get("OriginalArrivalTime") or result.get("id", "")
    print(f"Message sent. (id: {msg_id})")


# ── CLI ────────────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="teams.py",
        description="Read Microsoft Teams channels AND chats. Auth is automatic.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Channel commands (Graph API):
  python3 teams.py token
  python3 teams.py parse-url "https://teams.microsoft.com/l/channel/..."
  python3 teams.py teams
  python3 teams.py channels --team fc58da2f-...
  python3 teams.py messages --team ID --channel ID --top 50 --pages 4
  python3 teams.py replies  --team ID --channel ID --thread ID
  python3 teams.py unanswered --team ID --channel ID --minutes 480
  python3 teams.py scan --team ID --date 2026-03-21 --pages 3

Chat commands (Skype/Chat API):
  python3 teams.py chats                        # List all chats
  python3 teams.py chats --type group            # Only group chats
  python3 teams.py unread                        # List unread chats
  python3 teams.py unread --type 1:1             # Unread 1:1 chats only
  python3 teams.py chat-messages --chat <CONV_ID> # Read messages in a chat
  python3 teams.py send-message --chat <CONV_ID> --message "Hello"  # Send (with confirmation)
        """,
    )
    sub = p.add_subparsers(dest="command", metavar="command")

    # token
    sub.add_parser("token", help="Force token renewal and show expiry")

    # parse-url
    pu = sub.add_parser("parse-url", help="Extract IDs from a Teams URL")
    pu.add_argument("url", nargs="?", default="", help="Teams URL to parse")

    # teams
    t = sub.add_parser("teams", help="List all teams you belong to")
    t.add_argument("--json", action="store_true")

    # channels
    ch = sub.add_parser("channels", help="List channels in a team")
    ch.add_argument("--team", required=True)
    ch.add_argument("--json", action="store_true")

    # messages
    msg = sub.add_parser("messages", help="Recent messages in a channel")
    msg.add_argument("--team", required=True)
    msg.add_argument("--channel", required=True)
    msg.add_argument("--top", type=int, default=20)
    msg.add_argument("--pages", type=int, default=1)
    msg.add_argument("--since", default="", help="ISO8601 datetime filter")
    msg.add_argument("--json", action="store_true")

    # replies
    rep = sub.add_parser("replies", help="Show a thread and its replies")
    rep.add_argument("--team", required=True)
    rep.add_argument("--channel", required=True)
    rep.add_argument("--thread", required=True)
    rep.add_argument("--top", type=int, default=50)
    rep.add_argument("--json", action="store_true")

    # unanswered
    un = sub.add_parser("unanswered", help="Posts with no replies in last N min")
    un.add_argument("--team", required=True)
    un.add_argument("--channel", required=True)
    un.add_argument("--minutes", type=int, default=120)

    # scan
    sc = sub.add_parser("scan", help="All channel activity on a specific date")
    sc.add_argument("--team", required=True)
    sc.add_argument("--date", required=True, help="YYYY-MM-DD")
    sc.add_argument("--top", type=int, default=50)
    sc.add_argument(
        "--pages",
        type=int,
        default=2,
        help="Pages to paginate per channel (default: 2)",
    )

    # chats
    cht = sub.add_parser("chats", help="List all chats (group, 1:1, meetings)")
    cht.add_argument("--type", choices=["group", "1:1", "meeting", "other"], default="", help="Filter by chat type")
    cht.add_argument("--top", type=int, default=50, help="Max conversations to fetch")
    cht.add_argument("--json", action="store_true")

    # unread
    ur = sub.add_parser("unread", help="List chats with unread messages")
    ur.add_argument("--type", choices=["group", "1:1", "meeting", "other"], default="", help="Filter by chat type")
    ur.add_argument("--json", action="store_true")

    # chat-messages
    cm = sub.add_parser("chat-messages", help="Read messages from a specific chat")
    cm.add_argument("--chat", required=True, help="Conversation ID (from 'chats' or 'unread' output)")
    cm.add_argument("--top", type=int, default=30, help="Max messages to fetch")
    cm.add_argument("--json", action="store_true")

    # send-message
    sm = sub.add_parser("send-message", help="Send a message to a chat (requires confirmation)")
    sm.add_argument("--chat", required=True, help="Conversation ID to send to")
    sm.add_argument("--message", required=True, help="Message text to send")
    sm.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt (use with caution)")

    return p


COMMANDS = {
    "token": cmd_token,
    "parse-url": cmd_parse_url,
    "teams": cmd_teams,
    "channels": cmd_channels,
    "messages": cmd_messages,
    "replies": cmd_replies,
    "unanswered": cmd_unanswered,
    "scan": cmd_scan,
    "chats": cmd_chats,
    "unread": cmd_unread,
    "chat-messages": cmd_chat_messages,
    "send-message": cmd_send_message,
}


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    handler = COMMANDS.get(args.command)
    if not handler:
        parser.print_help()
        sys.exit(1)

    handler(args)


if __name__ == "__main__":
    main()
