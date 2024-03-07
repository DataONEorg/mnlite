# mnonboard

This module is designed to provide a wrapper around `opersist` and `mnlite` in order to streamline the [DataONE member node onboarding process](https://github.com/DataONEorg/mnlite/blob/feature/onboarding/docs/operation.md).
It takes as input either a json document manually edited from a template, or converts direct user input to a json document.

## Usage

This script requires working installations of both [sonormal](https://github.com/datadavev/sonormal) and [mnlite](https://github.com/DataONEorg/mnlite) to function properly.

### CLI options

```
Usage: cli [ OPTIONS ]
where OPTIONS := {
    -c | --check=[ NUMBER ]
            number of random metadata files to check for schema.org compliance
    -d | --dump=[ FILE ]
            dump default member node json file to configure manually
    -h | --help
            display this help message
    -i | --init
            initialize a new member node from scratch
    -l | --load=[ FILE ]
            initialize a new member node from a json file
    -P | --production
            run this script in production mode (uses the D1 cn API in searches)
    -L | --local
            run this script in local mode (will not scrape the remote site for new metadata)
}
```

### Onboarding process

Let's say you are in the `mnlite` base directory.
Start by activating the `mnlite` virtual environment and changing the working directory to `./mnonboard`:

```
workon mnlite
cd mnonboard
```

**Note:** Node data is stored in `instance/nodes/<NODENAME>`

#### Using an existing `node.json`

To onboard a member node with an existing `node.json` file:

```
python cli.py -l ../instance/nodes/BONARES/node.json
```

The script will guide you through the steps to set up the node and harvest its metadata.

#### No existing `node.json`

The script can also ask the user questions to set up the `node.json` file in an assisted manner. To do so, use the `-i` (initialize) flag:

```
python cli.py -i
```

Keep in mind that you should always check the `node.json` file to ensure correct values.

## Other functionality

Coming soon (see [#21](https://github.com/DataONEorg/mnlite/issues/21))
