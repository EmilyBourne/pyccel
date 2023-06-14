import jwt
import os
import time
import requests

def get_authorization():
    signing_key = jwt.jwk_from_pem(bytes(os.environ["PEM"], "utf-8"))
    # Issued at time
    # JWT expiration time (10 minutes maximum)
    # GitHub App's identifier
    payload = {'iat': int(time.time()), 'exp': int(time.time()) + 60, 'iss': 337566}

    jw_token=jwt.JWT().encode(payload, signing_key, alg='RS256')

    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {jw_token}", "X-GitHub-Api-Version": "2022-11-28"}

    # Create JWT
    reply = requests.post("https://api.github.com/app/installations/37820767/access_tokens", headers=headers)

    token  = reply.json()["token"]
    expiry = reply.json()["expires_at"]

    with open(os.environ["GITHUB_ENV"], "r") as f:
        output = f.read()

    if "installation_token" in output:
        lines = output.split('\n')
        print(lines)
        output = '\n'.join(l for l in lines if "installation_token" not in l)

    with open(os.environ["GITHUB_ENV"], "w") as f:
        f.write(output)
        print(f"installation_token={token}", file=f)
        print(f"installation_token_exp={expiry}", file=f)

    return token, expiry

class GitHubAPIInteractions:
    def __init__(self):
        repo = os.environ["GITHUB_REPOSITORY"]
        self._org, self._repo = repo.split('/')
        if "installation_token" in os.environ:
            self._install_token = os.environ["installation_token"]
            self._install_token_exp = time.strptime(os.environ["installation_token_exp"], "%Y-%m-%dT%H:%M:%SZ")
        else:
            self._install_token, expiry = get_authorization()
            self._install_token_exp = time.strptime(expiry, "%Y-%m-%dT%H:%M:%SZ")

    def _post_request(self, method, url, json=None, **kwargs):
        reply = requests.request(method, url, json=json, headers=self.get_headers(), **kwargs)
        return reply

    def check_runs(self, commit):
        url = f"https://api.github.com/repos/{self._org}/{self._repo}/commits/{commit}/check-runs"
        return self._post_request("GET", url).json()

    def create_run(self, commit, name):
        url = f"https://api.github.com/repos/{self._org}/{self._repo}/check-runs"
        workflow_url = f"https://github.com/{self._org}/{self._repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
        print("create_run:", url)
        json = {"name": name,
                "head_sha": commit,
                "status": "in_progress",
                "details_url": workflow_url}
        run = self._post_request("POST", url, json)
        assert run.status_code == 201
        return run.json()

    def prepare_run(self, commit, name):
        url = f"https://api.github.com/repos/{self._org}/{self._repo}/check-runs"
        json = {"name": name,
                "head_sha": commit,
                "status": "queued"}
        run = self._post_request("POST", url, json)
        assert run.status_code == 201
        return run.json()

    def update_run(self, run_id, json):
        url = f"https://api.github.com/repos/{self._org}/{self._repo}/check-runs/{run_id}"
        run = self._post_request("PATCH", url, json)
        assert run.status_code == 200
        return run

    def get_pr_details(self, pr_id):
        url = f"https://api.github.com/repos/{self._org}/{self._repo}/pulls/{pr_id}"
        print(url)
        return self._post_request("GET", url).json()

    def run_workflow(self, filename, inputs):
        # Create a workflow dispatch event (https://docs.github.com/en/rest/actions/workflows?apiVersion=2022-11-28)
        url = f"https://api.github.com/repos/{self._org}/{self._repo}/actions/workflows/{filename}/dispatches"
        json = {"ref": "devel",
                "inputs": inputs}
        print(url, json)
        return self._post_request("POST", url, json)

    def get_comments(self, pr_id):
        # Inspect comments (https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28)
        url = f"https://api.github.com/repos/{self._org}/{self._repo}/issues/{pr_id}/comments"
        return self._post_request("GET", url)

    def create_comment(self, pr_id, comment):
        url = f"https://api.github.com/repos/{self._org}/{self._repo}/issues/{pr_id}/comments"
        return self._post_request("POST", url, json={"body":comment})

    def create_review(self, pr_id, commit, comment, comments = ()):
        status = 'APPROVE' if len(comments)==0 else 'REQUEST_CHANGES'
        url = f"https://api.github.com/repos/{self._org}/{self._repo}/pulls/{pr_id}/reviews"
        review = {'commit_id':commit, 'body': comment, 'event': status, 'comments': comments}
        print(review)
        reply = self._post_request("POST", url, json=review)
        print(reply.text)
        assert reply.status_code == 200
        return reply

    def check_for_user_in_team(self, user, team):
        url = f'https://api.github.com/orgs/{self._org}/teams/{team}/membersips/{user}'
        return self._post_request("GET", url).json()

    def get_merged_prs(self):
        url = f'https://api.github.com/repos/{self._org}/{self._repo}/pulls'
        return self._post_request("GET", url).json()

    def get_check_runs(self, commit):
        url = f'https://api.github.com/repos/{self._org}/{self._repo}/commits/{commit}/check-runs'
        return self._post_request("GET", url).json()

    def get_pr_events(self, pr_id):
        url = f"https://api.github.com/repos/{self._org}/{self._repo}/issues/{pr_id}/events"
        return self._post_request("GET", url).json()

    def get_artifacts(self, name):
        url = f"https://api.github.com/repos/{self._org}/{self._repo}/actions/artifacts"
        query= {'name': name}
        return self._post_request("GET", url).json()
 
    def download_artifact(self, name, url):
        reply = self._post_request("GET", url, stream=True)
        with open(name, 'wb') as f:
            f.write(reply.content)


    def get_headers(self):
        if self._install_token_exp < time.struct_time(time.gmtime()):
            self._install_token, expiry = get_authorization()
            self._install_token_exp = time.strptime(expiry, "%Y-%m-%dT%H:%M:%SZ")

        return {"Accept": "application/vnd.github+json",
                 "Authorization": f"Bearer {self._install_token}",
                 "X-GitHub-Api-Version": "2022-11-28"}
