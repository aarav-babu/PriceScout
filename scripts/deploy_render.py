"""Deploy the tested main commit without printing the secret hook or response."""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def main():
    sha = os.environ['GITHUB_SHA']
    repo = os.environ['GITHUB_REPOSITORY']
    request = urllib.request.Request(
        f'https://api.github.com/repos/{repo}/git/ref/heads/main',
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                 'Accept': 'application/vnd.github+json', 'User-Agent': 'PriceScout-CI'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            latest = json.load(response)['object']['sha']
    except Exception:
        sys.exit('Could not verify the current main commit. No deploy was requested.')
    if latest != sha:
        print('A newer main commit exists; skipping this superseded deployment.')
        return

    hook = urllib.parse.urlsplit(os.environ.get('RENDER_DEPLOY_HOOK', ''))
    if hook.scheme != 'https' or hook.netloc != 'api.render.com' or not hook.path.startswith('/deploy/'):
        sys.exit('RENDER_DEPLOY_HOOK is missing or invalid. Set the GitHub Actions secret.')
    query = dict(urllib.parse.parse_qsl(hook.query))
    query['ref'] = sha
    target = urllib.parse.urlunsplit(hook._replace(query=urllib.parse.urlencode(query)))
    # HTTP exceptions may contain the credential-bearing URL: never print them.
    try:
        with urllib.request.urlopen(urllib.request.Request(target, method='POST'), timeout=30) as response:
            if response.status not in (200, 202):
                sys.exit('Render did not accept the deployment request.')
    except Exception:
        sys.exit('Render deployment request failed. Check the saved deploy hook and Render dashboard.')
    print('Render accepted the deployment request; waiting for revision ' + sha)
    deadline = time.monotonic() + 12 * 60
    health_url = 'https://pricescout-urwq.onrender.com/healthz'
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=20) as response:
                health = json.load(response)
            if health.get('status') == 'ok' and health.get('revision') == sha:
                print('Production is healthy and running the tested commit.')
                return
        except (urllib.error.URLError, TimeoutError, ValueError):
            pass
        time.sleep(15)
    sys.exit('The tested revision did not become healthy in time. Check Render build/deploy logs.')


if __name__ == '__main__':
    main()
