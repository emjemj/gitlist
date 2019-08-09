import argparse
import yaml
import os
import copy
import sys
import stat
import time

from dulwich import porcelain
from dulwich.objects import Blob
from dulwich.repo import MemoryRepo


class GitList:

    def __init__(self, config):
        self._parse_config(config)

    @classmethod
    def skeleton(cls, path):
        """ Generate a skeleton entity file and write to path """
        obj = {
            "description": "A description",
            "entity": "AS-SAMPLE",
        }

        fpath = "{}.yml".format(path)
        cls.write(fpath, obj)

    def run(self):
        """ Loop over yml files in repo and pull them from irr """

        repo = GitRepo(self.repo_path)
        commit = False

        for f in repo:
            if f.path[-3:] != b'yml':
                continue
            contents = repo.read(f)

            old = yaml.load(contents, Loader=yaml.BaseLoader)
            new = copy.deepcopy(old)
            new['members'] = self._load_as_set(old['entity'])

            if old == new:
                print("No changes found")
            else:
                print("Found new prefixes")
                contents = yaml.dump(new, default_flow_style=False)

                repo.add(f.path, contents)
                commit = True

        if commit:
            print("Committing")
            repo.commit("Updated prefix lists")

    def _parse_config(self, config):
        """ Initialize from config file """
        with open(config, 'r') as stream:
            cfg = yaml.load(stream, Loader=yaml.BaseLoader)
            self.repo_path = cfg["repo"]["path"]

    def _load_as_set(self, as_set):
        """ load data with bgpq3 """
        obj = {'ipv4': [], 'ipv6': []}

        for e in self._run_bgpq3(['-3j4', as_set]):
            obj['ipv4'].append(e['prefix'])

        for e in self._run_bgpq3(['-3j6', as_set]):
            obj['ipv6'].append(e['prefix'])

        # Sort lists to avoid changes from ordering
        obj['ipv4'].sort()
        obj['ipv6'].sort()

        return obj

    def _run_bgpq3(self, cmd):
        import subprocess
        import json

        cmd = ['bgpq3'] + cmd

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd='/')
        output = p.communicate()

        return json.loads(output[0].decode("UTF-8"))["NN"]


class GitRepo:
    """ simple abstraction for dulwich """

    def __init__(self, url):
        """ initialize dulwich magic """
        self.repo_url = url

        # We have two repository handles, one for reading and one for writing.
        self.rorepo = MemoryRepo()
        self.rwrepo = MemoryRepo()
        self.rorepo.refs.set_symbolic_ref(b'HEAD', b'refs/heads/master')
        self.rwrepo.refs.set_symbolic_ref(b'HEAD', b'refs/heads/master')

        porcelain.fetch(self.rorepo, self.repo_url)
        porcelain.fetch(self.rwrepo, self.repo_url)

        self.rorepo[b'refs/heads/master'] = self.rorepo[
            b'refs/remotes/origin/master']
        self.rwrepo[b'refs/heads/master'] = self.rwrepo[
            b'refs/remotes/origin/master']

        self.rotree = self.rorepo[self.rorepo[b'HEAD'].tree]
        self.rwtree = self.rwrepo[self.rwrepo[b'HEAD'].tree]

    def __iter__(self):
        """ iterate over items in ro tree """
        for item in self.rotree.iteritems():
            yield item

    def read(self, item):
        """ Read contents of a file from the ro repo """
        _, contents = self.rorepo.object_store.get_raw(item.sha)

        return contents

    def add(self, name, contents):
        """ Add a file to the repository """
        blob = Blob.from_string(contents.encode('utf-8'))

        self.rwrepo.object_store.add_object(blob)

        self.rwtree.add(name, stat.S_IFREG, blob.id)

        self.rwrepo.object_store.add_object(self.rwtree)

    def commit(self, message, push=True):
        """ commit to repo and optionally push to remote """
        self.rwrepo.do_commit(
            message=message.encode('utf-8'),
            ref=b'refs/heads/master',
            tree=self.rwtree.id
        )

        if push:
            porcelain.push(self.rwrepo, self.repo_url, 'master')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "gitlist, version controlled prefix lists")
    parser.add_argument("--skeleton", help="Create a new source file",
                        required=False)
    parser.add_argument("--config", help="Configuration file",
                        required=False)
    args = parser.parse_args()

    if args.skeleton:
        # Initialize a new skeleton file
        GitList.skeleton(args.skeleton)
        sys.exit(0)

    if not args.config:
        print("Config not specified")
        sys.exit(1)

    GitList(args.config).run()
