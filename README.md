# fhir-structure-diff
A tool to provide a simple diff of two profiles.  The diff all provides context in terms of the base element definitions. 


## WIP
Currently supports diff same versions, but only minimally tested.  Also possible to use a different Jinja2 template for the output.  Fetches bases defintions from web, so needs a live connection.

From the root directory.  Example usage:

```shell
pip install -r requirements.txt
python src/fhir_structure_diff.py ./src/tests/data/CareConnect-AllergyIntolerance-1.json ./src/tests/data/CareConnect-GPC-AllergyIntolerance-1.json
```

will generate a file markdown.md.

use

```shell
python src/fhir_structure_diff.py --help
```

for help on parameters

[Example output](./src)

## TODO
Unit tests  
Extend to handle different versions

