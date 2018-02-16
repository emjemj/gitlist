import argparse
import yaml
import git
import os
import copy
import sys
import shutil

class GitList:

    def __init__(self, config):
        self._parse_config(config)

    @classmethod
    def skeleton(cls, path):
        """ Generate a skeleton entity file and write to path """
        obj ={
            "deploy_at": None,
            "description": "A description", 
            "entity": "AS-SAMPLE",
            "name": "CUST-AS65000",
        }

        fpath = "{}.yml".format(path)
        cls.write(fpath, obj)

    @classmethod
    def write(cls, path, contents):
        """ Write dict from contents to file in path """
        with open(path, "w") as stream:
            stream.write(yaml.dump(contents, default_flow_style=False))

    def run(self):
        """ Loop over yml files in repo and pull them from irr """
        repo = Repo(self.repo_path, self.workdir)
        repo.clone()

        commit = False
        for f in os.listdir(self.workdir):
            fpath = os.path.join(repo.workdir, f)
            if not os.path.isfile(fpath):
                # Ignore directories
                continue
            if not f[-3:] == "yml":
                # Ignore non-yaml files
                continue

            with open(fpath, 'r') as stream:
                old = yaml.load(stream)

                # Create a copy of the current dataset to enable diff later
                new = copy.deepcopy(old)

                #macro = loader.load_asset(old['entity'])
                macro = self._load_as_set(old['entity'])

                #if not 'members' in new:
                    #new['members'] = {}
                new['members'] = self._load_as_set(old['entity'])

                #new["members"]["ipv4"] = [ str(x) for x in macro.inet ]
                #new["members"]["ipv6"] = [ str(x) for x in macro.inet6 ]

                if old == new:
                    # No changes has been made to as-set
                    print("No changes found")
                else:
                    # New prefixes found, commit them
                    print("New prefixes found, commiting")
                    repo.add(f, new)
                    commit = True
        if commit:
            # some changes were made to the repo
            repo.commit()

        repo.cleanup()

    def _parse_config(self, config):
        """ Initialize from config file """
        with open(config, 'r') as stream:
            cfg = yaml.load(stream)
            self.repo_path = cfg["repo"]["path"]
            self.workdir = cfg["workdir"]

    def _load_as_set(self, as_set):
        """ load data with bgpq3 """
        obj = { 'ipv4': [], 'ipv6': [] }

        for e in self._run_bgpq3([ '-3j4', as_set ]):
            obj['ipv4'].append(e['prefix'])

        for e in self._run_bgpq3([ '-3j6', as_set ]):
            obj['ipv6'].append(e['prefix'])

        # Sort lists to avoid changes from ordering
        obj['ipv4'].sort()
        obj['ipv6'].sort()

        return obj

    def _run_bgpq3(self, cmd):
        import subprocess
        import json

        cmd = [ 'bgpq3'] + cmd

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, cwd='/')
        output = p.communicate()

        return json.loads(output[0].decode("UTF-8"))["NN"]

class Repo:
    """ Simple abstraction for gitpython """

    def __init__(self, path, workdir):
        """ path is a bare repo, workdir is a directory where we can 
            checkout the repo 
        """
        self.path = path
        self.workdir = workdir
        self.files_added = False

    @classmethod
    def init_bare(cls, path):
        """ Initialize bare git repo """
        repo = git.Repo.init(path, bare=True)

    def clone(self):
        """ Clone our bare repo """
        self.bare_repo = git.repo.Repo(self.path)
        self.repo = self.bare_repo.clone(self.workdir)

    def add(self, filename, contents):
        """ Add a file to commit """
        path = os.path.join(self.workdir, filename)

        GitList.write(path, contents)

        self.repo.index.add([path])
        self.files_added = True

    def commit(self, message='Files updated'):
        """ Commit added files to repo """
        if not self.files_added:
            return

        self.repo.index.commit(message)
        self.repo.remotes.origin.push()

    def cleanup(self):
        """ Remove workdir """
        shutil.rmtree(self.workdir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser("gitlist, version controlled prefix lists")
    parser.add_argument("--init-bare", help="Initialize a new repository",
                        required=False)
    parser.add_argument("--skeleton", help="Create a new source file",
                        required=False)
    parser.add_argument("--config", help="Configuration file",
                        required=False)
    args = parser.parse_args()

    if args.init_bare:
        # Initialize a new git repo
        Repo.init_bare(args.init_bare)
        sys.exit(0)

    if args.skeleton:
        # Initialize a new skeleton file
        GitList.skeleton(args.skeleton)
        sys.exit(0)

    if not args.config:
        print("Config not specified")
        sys.exit(1)

    GitList(args.config).run()
