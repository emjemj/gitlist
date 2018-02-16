# gitlist

A simple tool to generate (and soon deploy) prefix-lists for your downstream customers. A log of changes to the lists are stored in git.

## Installation

### Requirements
gitlist depends on a number of other projects

 * bgpq3
 * python
 * gitpython
 * pyyaml

### Configuration
A small configuration is needed, it looks like this. Please adjust paths as necessary

```yaml
repo:
 path: /var/lib/gitlist/datastore.git
workdir: /tmp/gitlist.scratch
```

### Initial setup
Initialize git repo with `gitlist.py --init-bare <path>`. You then need to add source files to your recently created git repository.

Clone to a temporary place, add a skeleton file with `gitlist.py --skeleton <path>` and edit it. You then commit and push the newly created file.

### Fetching and updating data
Run `gitlist.py --config <path>` to fetch prefixes from IRR. These will be added under the members key in the entity file and commited to your repository. 
