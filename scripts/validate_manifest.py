#!/usr/bin/env python3
"""Validate the Trust bootstrap manifest (manifestVersion 1)."""

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "dist" / "manifest.json"

RELEASE_ID = re.compile(r"^r[0-9]{6}$")
SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
SECRET_MARKERS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "bearer ",
    "private_key",
    "aws_access",
    "BEGIN PRIVATE",
)

REQUIRED_URLS = (
    ("application", "website"),
    ("links", "privacy"),
    ("links", "support"),
    ("links", "terms"),
)


class ManifestError(Exception):
    pass


def load_manifest(path):
    raw = Path(path).read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ManifestError("manifest must be UTF-8 without a BOM")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ManifestError("manifest must be UTF-8") from error
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ManifestError("manifest is not valid JSON: {}".format(error)) from error
    if not isinstance(document, dict):
        raise ManifestError("manifest must be a JSON object")
    lowered = text.lower()
    for marker in SECRET_MARKERS:
        if marker in lowered:
            raise ManifestError("manifest contains a forbidden secret-like marker")
    return document


def parse_utc(value, field):
    if not isinstance(value, str) or not value:
        raise ManifestError("{} must be an ISO-8601 UTC timestamp".format(field))
    if value.endswith("Z"):
        candidate = value[:-1] + "+00:00"
    else:
        candidate = value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise ManifestError("{} is not ISO-8601: {}".format(field, value)) from error
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ManifestError("{} must be UTC".format(field))
    return parsed


def require_https(value, field):
    if not isinstance(value, str) or not value.startswith("https://") or " " in value:
        raise ManifestError("{} must be an HTTPS URL".format(field))
    return value


def require_object(document, field):
    value = document.get(field)
    if not isinstance(value, dict):
        raise ManifestError("{} must be an object".format(field))
    return value


def require_semver(value, field):
    if not isinstance(value, str) or SEMVER.fullmatch(value) is None:
        raise ManifestError("{} must be a MAJOR.MINOR.PATCH version".format(field))
    return tuple(int(part) for part in value.split("."))


def validate(document):
    version = document.get("manifestVersion")
    if type(version) is not int or version < 1:
        raise ManifestError("manifestVersion must be an integer >= 1")
    if version != 1:
        raise ManifestError("this validator implements manifestVersion 1 only")

    parse_utc(document.get("generatedAt"), "generatedAt")
    if document.get("environment") != "production":
        raise ManifestError("environment must be production")

    application = require_object(document, "application")
    if not isinstance(application.get("name"), str) or not application["name"].strip():
        raise ManifestError("application.name is required")
    require_https(application.get("website"), "application.website")

    links = require_object(document, "links")
    for key in ("privacy", "support", "terms"):
        require_https(links.get(key), "links.{}".format(key))

    service = document.get("service", {})
    if service is not None:
        if not isinstance(service, dict):
            raise ManifestError("service must be an object")
        status = service.get("status")
        if status is not None and status not in ("active", "degraded", "maintenance"):
            raise ManifestError("service.status is not a known value")

    catalog = require_object(document, "catalog")
    schema_version = catalog.get("schemaVersion")
    if type(schema_version) is not int or schema_version < 1:
        raise ManifestError("catalog.schemaVersion must be an integer >= 1")
    release = catalog.get("release")
    if not isinstance(release, str) or RELEASE_ID.fullmatch(release) is None:
        raise ManifestError("catalog.release must match rNNNNNN")
    created = parse_utc(catalog.get("createdAt"), "catalog.createdAt")
    published = parse_utc(catalog.get("publishedAt"), "catalog.publishedAt")
    if published < created:
        raise ManifestError("catalog.publishedAt is earlier than catalog.createdAt")
    download_url = require_https(catalog.get("downloadUrl"), "catalog.downloadUrl")
    if not download_url.endswith(".zip"):
        raise ManifestError("catalog.downloadUrl must name the zip artifact")
    release_url = require_https(catalog.get("releaseUrl"), "catalog.releaseUrl")
    if release not in release_url or release not in download_url:
        raise ManifestError("catalog URLs must include the release id")
    if not download_url.startswith(release_url.rstrip("/") + "/"):
        raise ManifestError("catalog.downloadUrl must be beneath catalog.releaseUrl")

    size = catalog.get("sizeBytes")
    if type(size) is not int or size <= 0:
        raise ManifestError("catalog.sizeBytes must be an integer > 0")
    digest = catalog.get("sha256")
    if not isinstance(digest, str) or SHA256_HEX.fullmatch(digest) is None:
        raise ManifestError("catalog.sha256 must be 64 lowercase hex characters")

    content_type = catalog.get("contentType")
    if content_type is not None and content_type != "application/zip":
        raise ManifestError("catalog.contentType must be application/zip when present")
    compression = catalog.get("compression")
    if compression is not None and compression != "zip":
        raise ManifestError("catalog.compression must be zip when present")

    compatibility = catalog.get("compatibility")
    if not isinstance(compatibility, dict):
        raise ManifestError("catalog.compatibility is required")
    minimum = require_semver(
        compatibility.get("minimumApplicationVersion"),
        "catalog.compatibility.minimumApplicationVersion",
    )
    maximum = compatibility.get("maximumApplicationVersion")
    if maximum is not None:
        maximum_version = require_semver(
            maximum, "catalog.compatibility.maximumApplicationVersion"
        )
        if maximum_version < minimum:
            raise ManifestError("maximumApplicationVersion is below the minimum")

    cache = document.get("cache")
    if cache is not None:
        if not isinstance(cache, dict):
            raise ManifestError("cache must be an object")
        interval = cache.get("recommendedCheckIntervalSeconds")
        if type(interval) is not int or interval < 3600:
            raise ManifestError(
                "cache.recommendedCheckIntervalSeconds must be an integer >= 3600"
            )
        stale = cache.get("staleIfOffline")
        if not isinstance(stale, bool):
            raise ManifestError("cache.staleIfOffline must be a boolean")

    return document


def verify_artifact(document):
    catalog = document["catalog"]
    url = catalog["downloadUrl"]
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": "ScottsTCGBinder-ManifestValidator/1"},
    )
    try:
        response_context = urllib.request.urlopen(request, timeout=120)
    except urllib.error.URLError as error:
        raise ManifestError("catalog download failed: {}".format(error)) from error
    with response_context as response:
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
        payload = response.read()
    if content_type != "application/zip":
        raise ManifestError(
            "downloaded content type is {}, expected application/zip".format(content_type)
        )
    if len(payload) != catalog["sizeBytes"]:
        raise ManifestError(
            "downloaded size {} does not match sizeBytes {}".format(
                len(payload), catalog["sizeBytes"]
            )
        )
    digest = hashlib.sha256(payload).hexdigest()
    if digest != catalog["sha256"]:
        raise ManifestError("downloaded sha256 does not match catalog.sha256")
    return digest


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "manifest",
        nargs="?",
        default=str(DEFAULT_MANIFEST),
        help="path to manifest.json",
    )
    parser.add_argument(
        "--verify-artifact",
        action="store_true",
        help="download catalog.downloadUrl and check size and sha256",
    )
    args = parser.parse_args(argv)
    try:
        document = validate(load_manifest(args.manifest))
        if args.verify_artifact:
            verify_artifact(document)
    except ManifestError as error:
        print("FAIL {}".format(error), file=sys.stderr)
        return 1
    print("OK {}".format(args.manifest))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
