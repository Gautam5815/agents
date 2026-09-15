import requests

from . import config

API_BASE = "https://api.linkedin.com/v2"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.LINKEDIN_ACCESS_TOKEN}",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def get_person_urn() -> str:
    """Fetch the authenticated member's URN using the OpenID userinfo endpoint.
    Requires the 'openid' and 'profile' scopes on the access token."""
    config.require("LINKEDIN_ACCESS_TOKEN")
    resp = requests.get(USERINFO_URL, headers=_headers(), timeout=20)
    resp.raise_for_status()
    sub = resp.json()["sub"]
    return f"urn:li:person:{sub}"


def _register_image_upload(person_urn: str) -> tuple[str, str]:
    """Registers an image upload and returns (upload_url, asset_urn)."""
    body = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": person_urn,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent",
                }
            ],
        }
    }
    resp = requests.post(
        f"{API_BASE}/assets?action=registerUpload",
        headers={**_headers(), "Content-Type": "application/json"},
        json=body,
        timeout=20,
    )
    resp.raise_for_status()
    value = resp.json()["value"]
    upload_url = value["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset_urn = value["asset"]
    return upload_url, asset_urn


def _upload_image_bytes(upload_url: str, image_bytes: bytes) -> None:
    resp = requests.put(
        upload_url,
        headers={"Authorization": f"Bearer {config.LINKEDIN_ACCESS_TOKEN}"},
        data=image_bytes,
        timeout=60,
    )
    resp.raise_for_status()


def resolve_author_urn() -> str:
    """Determine which LinkedIn entity to post as. Posting as the Trynocode company page
    (LINKEDIN_ORG_URN, requires w_organization_social + page admin access) takes priority
    over posting as a personal profile."""
    if config.LINKEDIN_ORG_URN:
        return config.LINKEDIN_ORG_URN
    return config.LINKEDIN_PERSON_URN or get_person_urn()


def post_with_image_bytes(text: str, image_bytes: bytes, author_urn: str | None = None) -> dict:
    """Publish a LinkedIn post with an attached image given as raw bytes.
    Returns the created post's response JSON. This has no local disk dependency,
    so it's the version used by the serverless (Vercel) app."""
    config.require("LINKEDIN_ACCESS_TOKEN")

    author = author_urn or resolve_author_urn()

    upload_url, asset_urn = _register_image_upload(author)
    _upload_image_bytes(upload_url, image_bytes)

    body = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "media": asset_urn,
                    }
                ],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    resp = requests.post(
        f"{API_BASE}/ugcPosts",
        headers={**_headers(), "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    return {"status_code": resp.status_code, "post_id": resp.headers.get("x-restli-id")}


def post_with_image(text: str, image_path: str, author_urn: str | None = None) -> dict:
    """Publish a LinkedIn post with an image read from a local file path (CLI use)."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    return post_with_image_bytes(text, image_bytes, author_urn=author_urn)
