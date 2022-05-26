import os
from jinja2 import Template
from lib import profile_diff as pd
from lib import profile_args
from lib import profile_mappings


def fhir_structure_diff(args):

    mappings = profile_mappings.extract_mapping(args)
    print(mappings)

    element_level_diff = pd.element_diff(args.leftprofile, args.rightprofile)
    component_level_diff = pd.component_diff(args.leftprofile, args.rightprofile, args.leftversion)  # TODO support multiple versions

    diff_template = open(args.template).read()
    t = Template(diff_template)
    diff_rendered = t.render(resource_type=args.leftprofile['type'],
                             left_profile=args.leftprofile['name'],
                             left_version=args.leftversion,
                             right_profile=args.rightprofile['name'],
                             right_version=args.rightversion,
                             element_level_diff=element_level_diff,
                             component_results=component_level_diff)

    diff_file = './' + os.path.basename(args.template).rsplit('.', 1)[0]
    diff = open(diff_file, 'w')
    diff.write(diff_rendered)


def main():
    args = profile_args.get_args()
    fhir_structure_diff(args)


if __name__ == "__main__":
    main()
