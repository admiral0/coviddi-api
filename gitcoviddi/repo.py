from git_adapter.git import Git, CmdError
from datetime import datetime
from dataclasses import dataclass
from dateutil.parser import parse
import re


COMMIT_RE = re.compile(r'^commit\s+([a-f0-9]+)$')
DATE_RE = re.compile(r'^Date:\s+(.+)$')

def _build_git_or_die_tryin(path):
    g = Git(path)
    g.status()
    return g

@dataclass
class GitInfo:
    commit_id: str
    commit_time: datetime

class GitRepo:
    info: GitInfo

    def __init__(self, repository, path):
        try:
            self.g = _build_git_or_die_tryin(path)
        except CmdError:
            self.g = Git.clone_repo(repository, path)
        self.info = GitInfo('unknown', datetime.fromtimestamp(0))

        self._refresh_info()
    def poll(self):
        updated = len(self.g.fetch().lines) > 0
        if updated:
            self._refresh_info()
        return updated

    def _refresh_info(self):
        last_commit = self.g.log("-1")
        for line in last_commit:
            m = COMMIT_RE.match(line)
            if m:
                self.info.commit_id = m.group(1)
            m = DATE_RE.match(line)
            if m:
                self.info.commit_time = parse(m.group(1))

