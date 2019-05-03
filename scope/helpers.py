from urllib.parse import urlparse


def ss_hosts_parser(hosts):
    """Parse a list of SS URLs.

    Transform a list of RFC-1738 formatted URLs to a list of dictionaries
    with "url", "user" and "secret" keys.
    """
    parsed_hosts = {}
    for host in hosts:
        parts = urlparse(host)
        # Raise on malformed URLs
        if (
            not parts.scheme
            or not parts.hostname
            or (parts.port and type(parts.port) is not int)
        ):
            raise ValueError("Malformed SS host: %s" % host)
        # Raise if credentials are not present
        if not parts.username or not parts.password:
            raise ValueError("Missing credentials for SS host: %s" % host)
        url = "%s://%s" % (parts.scheme, parts.hostname)
        if parts.port:
            url = "%s:%s" % (url, parts.port)
        parsed_hosts[url] = {"user": parts.username, "secret": parts.password}
    return parsed_hosts
