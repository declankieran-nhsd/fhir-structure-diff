import os
import json


def read_structuremap(filename):
    print(filename)
    input_file_extension = os.path.splitext(filename)[1]

    if input_file_extension.lower() == '.json':
        map = json.load(open(filename))
        # Must at least have one rule
        check_structuremap(map)
        return map

    elif input_file_extension.lower() == '.xml':
        raise NotImplementedError('XML type not implemented.')

    elif input_file_extension.lower() == '.ttl':
        raise NotImplementedError('Turtle type not implemented.')

    else:
        raise TypeError('Unrecognised file extension: ' + input_file_extension)


def check_structuremap(map):
    # TODO might be useful to compare profiles with structure.url, but leave for now
    if not isinstance(map, dict):
        raise ValueError('Unexpected data for StructureMap.\n\nContents -> ' + str(map))

    if 'group' not in map.keys():
        raise ValueError('No group section found in map.\n\nMap -> ' +
                         json.dumps(map, indent=2))

    # TODO not sure this is necessary or correct
    for group in map['group']:
        if 'rule' not in group:
            raise ValueError('No rules in group section.\n\nMap -> ' +
                             json.dumps(map, indent=2))
