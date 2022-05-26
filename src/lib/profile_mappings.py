import os
from .structuremap_reader import read_structuremap

# TODO for now going to assume the structuremaps are in the local cache

LOCAL_PACKAGE_CACHE = '../tests/data/'
DEFAULT_FHIR_PACKAGE_CACHE = os.path.expanduser('~/.fhir/packages/hl7.fhir.xver.r4#1.2.0/package/')


def extract_mapping(args):
    if args.leftversion == args.rightversion:
        return 'some kind of default'

    # TODO handle download of structure maps
    # Example <cache-path>/StructureMap-AllergyIntolerance3to4.json
    structuremap = DEFAULT_FHIR_PACKAGE_CACHE + 'StructureMap-' + \
                   args.leftprofile['type'] + args.leftversion[0] + 'to' + args.rightversion[0] + '.json'

    if not os.path.isfile(structuremap):
        raise FileNotFoundError("The StructureMap does not exist at " + structuremap)

    map = read_structuremap(structuremap)

    # Scan for name of all groups, will be used to determine if dependent is a local group (function)
    # type-and-types seems to designate the main group (function)
    # assuming name in a group set is unique
    group_types = {}
    main_group = []
    local_groups = []
    for group in map['group']:
        if 'name' in group and 'typeMode' in group:
            if group['typeMode'] == 'type-and-types':
                main_group.append(group)
            else:
                group_types[group['name']] = group['typeMode']
                local_groups.append(group)
        else:
            raise ValueError('Group is missing required element, name or typeMode.\n\nGroup -> ' + group)

    # Assuming type-and-types is the primary group, this doesn't seem to be true for StructureMaps for some primitives
    # TODO: Understanding the rules better around this would be useful, also skipping data validation of 'rule; in group
    if len(main_group) > 1:
        raise ValueError('Multiple groups with typeMode: type-and-types, is not supported.')

    # Scan for simple mappings, which include
    # - Has a source and target
    # - Does not have a dependent that is a local group (function)
    # TODO: Assuming in-built groups (library functions, e.g. Reference etc...) may still diff in terms of internal
    # TODO: elements between versions, although maybe not, it'd be worth checking this
    simple = {}
    dep_names = {}
    local_dependent = {}
    for rule in main_group[0]['rule']:
        if 'source' not in rule:
            raise ValueError('No source entry in rule:\n\nRule -> ' + rule)
        if 'dependent' in rule:
            # It seems there should generally only be 1 dependent if it exists, but it is 0..*
            # This is just a simple check, so its fine, but more than on dependent is also not considered here
            # TODO Skipping data validation of 'name' in d here for brevity
            dep_names[rule['name']] = [d['name'] for d in rule['dependent']]
            # Check if intersection of dependent names in rule and local group names is not empty
            dep_set = set(dep_names[rule['name']])
            if len(dep_set & set(group_types.keys())) > 0:
                # TODO another thing that wil need handle, just taking the first element of dependent
                local_dependent[[d['name'] for d in rule['dependent']][0]] = rule['source'][0]['element']
        if 'target' in rule:
            # Not considering the case where there may be more than one source or target
            # One scenario of multiple targets is where sub elements are being set, e.g.
            # FML:  src.element as v ->  tgt.extension as vt,  vt.url = 'abc',  vt.value = v;
            # TODO would be worth understanding all scenarios here, also skipped data validation 'name' in [0]
            simple[rule['source'][0]['element']] = rule['target'][0]['element']

    # Scan for mappings contained in local group functions
    for local in local_groups:
        for rule in local['rule']:
            # TODO this will crash if local['name'] doesn't exist in local_dependent, but I'd like to see if this happens
            # TODO leave for now, maybe until I run through a large set of profiles
            # TODO It will also crash if len(local['name']) > 1
            src_root_path = local_dependent[local['name']] + '.'
            if local_dependent[local['name']] in simple.keys():
                tgt_root_path = simple[local_dependent[local['name']]] + '.'
            else:
                tgt_root_path = ''

            # Just going to assume there will be no more dependent functions in the local dependent functions for now
            # TODO this will need a lot of error handling
            if 'source' not in rule or 'target' not in rule:
                raise ValueError('There must be a source and target in the rule.'
                                 'Dependent groups within local dependent groups not supported. \n\nRule -> ' + rule)

            # TODO I should really checkout the input variables and make sure they match source and target, e.g.
            # TODO something like
            # local_group_input_src = [key for key, value in local_group['input'] if value == 'source']
            # local_group_input_tgt = [key for key, value in local_group['input'] if value == 'target']
            src_path = src_root_path + rule['source'][0]['element']
            tgt_path = tgt_root_path + rule['target'][0]['element']
            simple[src_path] = tgt_path

    return simple


el_table1 = \
    [
        {
            "MedicationRequest.extension": (
                {
                    "id": "MedicationRequest.extension",
                    "path": "MedicationRequest.extension",
                    "slicing": {
                        "discriminator": [{"type": "value", "path": "url"}],
                        "rules": "open",
                    },
                    "base": {"path": "DomainResource.extension", "min": 0, "max": "*"},
                },
                {
                    "id": "MedicationRequest.extension",
                    "path": "MedicationRequest.extension",
                    "slicing": {
                        "discriminator": [{"type": "value", "path": "url"}],
                        "rules": "open",
                    },
                },
            )
        },
        {
            "MedicationRequest.identifier.assigner": (
                {
                    "id": "MedicationRequest.identifier.assigner",
                    "path": "MedicationRequest.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Organization-1",
                        }
                    ],
                    "base": {"path": "Identifier.assigner", "min": 0, "max": "1"},
                },
                {
                    "id": "MedicationRequest.identifier.assigner",
                    "path": "MedicationRequest.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.basedOn": (
                {
                    "id": "MedicationRequest.basedOn",
                    "path": "MedicationRequest.basedOn",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": "http://hl7.org/fhir/StructureDefinition/CarePlan",
                        },
                        {
                            "code": "Reference",
                            "targetProfile": "http://hl7.org/fhir/StructureDefinition/ProcedureRequest",
                        },
                        {
                            "code": "Reference",
                            "targetProfile": "http://hl7.org/fhir/StructureDefinition/ReferralRequest",
                        },
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-MedicationRequest-1",
                        },
                    ],
                    "base": {"path": "MedicationRequest.basedOn", "min": 0, "max": "*"},
                },
                {
                    "id": "MedicationRequest.basedOn",
                    "path": "MedicationRequest.basedOn",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "http://hl7.org/fhir/StructureDefinition/ImmunizationRecommendation",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-CarePlan",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-MedicationRequest",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-ServiceRequest",
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.groupIdentifier.assigner": (
                {
                    "id": "MedicationRequest.groupIdentifier.assigner",
                    "path": "MedicationRequest.groupIdentifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Organization-1",
                        }
                    ],
                    "base": {"path": "Identifier.assigner", "min": 0, "max": "1"},
                },
                {
                    "id": "MedicationRequest.groupIdentifier.assigner",
                    "path": "MedicationRequest.groupIdentifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.subject": (
                {
                    "id": "MedicationRequest.subject",
                    "path": "MedicationRequest.subject",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": "http://hl7.org/fhir/StructureDefinition/Group",
                        },
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Patient-1",
                        },
                    ],
                    "base": {"path": "MedicationRequest.subject", "min": 1, "max": "1"},
                },
                {
                    "id": "MedicationRequest.subject",
                    "path": "MedicationRequest.subject",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "http://hl7.org/fhir/StructureDefinition/Group",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Patient",
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.recorder": (
                {
                    "id": "MedicationRequest.recorder",
                    "path": "MedicationRequest.recorder",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Practitioner-1",
                        }
                    ],
                    "base": {"path": "MedicationRequest.recorder", "min": 0, "max": "1"},
                },
                {
                    "id": "MedicationRequest.recorder",
                    "path": "MedicationRequest.recorder",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Practitioner",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-PractitionerRole",
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.reasonReference": (
                {
                    "id": "MedicationRequest.reasonReference",
                    "path": "MedicationRequest.reasonReference",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Condition-1",
                        },
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Observation-1",
                        },
                    ],
                    "base": {
                        "path": "MedicationRequest.reasonReference",
                        "min": 0,
                        "max": "*",
                    },
                },
                {
                    "id": "MedicationRequest.reasonReference",
                    "path": "MedicationRequest.reasonReference",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Condition",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Observation",
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.note.author[x]": (
                {
                    "id": "MedicationRequest.note.author[x]",
                    "path": "MedicationRequest.note.author[x]",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": "http://hl7.org/fhir/StructureDefinition/RelatedPerson",
                        },
                        {"code": "string"},
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Patient-1",
                        },
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Practitioner-1",
                        },
                    ],
                    "base": {"path": "Annotation.author[x]", "min": 0, "max": "1"},
                },
                {
                    "id": "MedicationRequest.note.author[x]",
                    "path": "MedicationRequest.note.author[x]",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Practitioner",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Patient",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-RelatedPerson",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization",
                            ],
                        },
                        {"code": "string"},
                    ],
                },
            )
        },
        {
            "MedicationRequest.dispenseRequest.performer": (
                {
                    "id": "MedicationRequest.dispenseRequest.performer",
                    "path": "MedicationRequest.dispenseRequest.performer",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Organization-1",
                        }
                    ],
                    "base": {
                        "path": "MedicationRequest.dispenseRequest.performer",
                        "min": 0,
                        "max": "1",
                    },
                },
                {
                    "id": "MedicationRequest.dispenseRequest.performer",
                    "path": "MedicationRequest.dispenseRequest.performer",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.priorPrescription": (
                {
                    "id": "MedicationRequest.priorPrescription",
                    "path": "MedicationRequest.priorPrescription",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-MedicationRequest-1",
                        }
                    ],
                    "base": {
                        "path": "MedicationRequest.priorPrescription",
                        "min": 0,
                        "max": "1",
                    },
                },
                {
                    "id": "MedicationRequest.priorPrescription",
                    "path": "MedicationRequest.priorPrescription",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-MedicationRequest"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.extension:repeatInformation": (
                {
                    "id": "MedicationRequest.extension:repeatInformation",
                    "path": "MedicationRequest.extension",
                    "sliceName": "repeatInformation",
                    "type": [
                        {
                            "code": "Extension",
                            "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-CareConnect-MedicationRepeatInformation-1",
                        }
                    ],
                    "base": {"path": "DomainResource.extension", "min": 0, "max": "*"},
                },
                {},
            )
        },
        {
            "MedicationRequest.extension:statusReason": (
                {
                    "id": "MedicationRequest.extension:statusReason",
                    "path": "MedicationRequest.extension",
                    "sliceName": "statusReason",
                    "type": [
                        {
                            "code": "Extension",
                            "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-CareConnect-MedicationStatusReason-1",
                        }
                    ],
                    "base": {"path": "DomainResource.extension", "min": 0, "max": "*"},
                },
                {},
            )
        },
        {
            "MedicationRequest.extension:prescriptionType": (
                {
                    "id": "MedicationRequest.extension:prescriptionType",
                    "path": "MedicationRequest.extension",
                    "sliceName": "prescriptionType",
                    "type": [
                        {
                            "code": "Extension",
                            "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-CareConnect-PrescriptionType-1",
                        }
                    ],
                    "base": {"path": "DomainResource.extension", "min": 0, "max": "*"},
                },
                {},
            )
        },
        {
            "MedicationRequest.identifier.system": (
                {
                    "id": "MedicationRequest.identifier.system",
                    "path": "MedicationRequest.identifier.system",
                    "min": 1,
                    "base": {"path": "Identifier.system", "min": 0, "max": "1"},
                },
                {},
            )
        },
        {
            "MedicationRequest.identifier.value": (
                {
                    "id": "MedicationRequest.identifier.value",
                    "path": "MedicationRequest.identifier.value",
                    "min": 1,
                    "base": {"path": "Identifier.value", "min": 0, "max": "1"},
                },
                {},
            )
        },
        {
            "MedicationRequest.medicationReference:medicationReference": (
                {
                    "id": "MedicationRequest.medicationReference:medicationReference",
                    "path": "MedicationRequest.medicationReference",
                    "sliceName": "medicationReference",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Medication-1",
                        }
                    ],
                    "binding": {
                        "extension": [
                            {
                                "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-bindingName",
                                "valueString": "MedicationCode",
                            }
                        ],
                        "strength": "example",
                        "valueSetUri": "http://hl7.org/fhir/ValueSet/medication-codes",
                    },
                    "base": {
                        "path": "MedicationRequest.medication[x]",
                        "min": 1,
                        "max": "1",
                    },
                },
                {},
            )
        },
        {
            "MedicationRequest.context": (
                {
                    "id": "MedicationRequest.context",
                    "path": "MedicationRequest.context",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": "http://hl7.org/fhir/StructureDefinition/EpisodeOfCare",
                        },
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Encounter-1",
                        },
                    ],
                    "base": {"path": "MedicationRequest.context", "min": 0, "max": "1"},
                },
                {},
            )
        },
        {
            "MedicationRequest.requester.agent": (
                {
                    "id": "MedicationRequest.requester.agent",
                    "path": "MedicationRequest.requester.agent",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": "http://hl7.org/fhir/StructureDefinition/RelatedPerson",
                        },
                        {
                            "code": "Reference",
                            "targetProfile": "http://hl7.org/fhir/StructureDefinition/Device",
                        },
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Organization-1",
                        },
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Patient-1",
                        },
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Practitioner-1",
                        },
                    ],
                    "base": {
                        "path": "MedicationRequest.requester.agent",
                        "min": 1,
                        "max": "1",
                    },
                },
                {},
            )
        },
        {
            "MedicationRequest.requester.onBehalfOf": (
                {
                    "id": "MedicationRequest.requester.onBehalfOf",
                    "path": "MedicationRequest.requester.onBehalfOf",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Organization-1",
                        }
                    ],
                    "base": {
                        "path": "MedicationRequest.requester.onBehalfOf",
                        "min": 0,
                        "max": "1",
                    },
                },
                {},
            )
        },
        {
            "MedicationRequest.dosageInstruction.additionalInstruction.coding": (
                {
                    "id": "MedicationRequest.dosageInstruction.additionalInstruction.coding",
                    "path": "MedicationRequest.dosageInstruction.additionalInstruction.coding",
                    "slicing": {
                        "discriminator": [{"type": "value", "path": "system"}],
                        "ordered": False,
                        "rules": "open",
                    },
                    "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dosageInstruction.additionalInstruction.coding:snomedCT": (
                {
                    "id": "MedicationRequest.dosageInstruction.additionalInstruction.coding:snomedCT",
                    "path": "MedicationRequest.dosageInstruction.additionalInstruction.coding",
                    "sliceName": "snomedCT",
                    "max": "1",
                    "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dosageInstruction.additionalInstruction.coding:snomedCT.extension": (
                {
                    "id": "MedicationRequest.dosageInstruction.additionalInstruction.coding:snomedCT.extension",
                    "path": "MedicationRequest.dosageInstruction.additionalInstruction.coding.extension",
                    "slicing": {
                        "discriminator": [{"type": "value", "path": "url"}],
                        "rules": "open",
                    },
                    "base": {"path": "Element.extension", "min": 0, "max": "*"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dosageInstruction.additionalInstruction.coding:snomedCT.extension:snomedCTDescriptionID": (
                {
                    "id": "MedicationRequest.dosageInstruction.additionalInstruction.coding:snomedCT.extension:snomedCTDescriptionID",
                    "path": "MedicationRequest.dosageInstruction.additionalInstruction.coding.extension",
                    "sliceName": "snomedCTDescriptionID",
                    "type": [
                        {
                            "code": "Extension",
                            "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-coding-sctdescid",
                        }
                    ],
                    "base": {"path": "Element.extension", "min": 0, "max": "*"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dosageInstruction.additionalInstruction.coding:snomedCT.system": (
                {
                    "id": "MedicationRequest.dosageInstruction.additionalInstruction.coding:snomedCT.system",
                    "path": "MedicationRequest.dosageInstruction.additionalInstruction.coding.system",
                    "min": 1,
                    "fixedUri": "http://snomed.info/sct",
                    "base": {"path": "Coding.system", "min": 0, "max": "1"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dosageInstruction.additionalInstruction.coding:snomedCT.code": (
                {
                    "id": "MedicationRequest.dosageInstruction.additionalInstruction.coding:snomedCT.code",
                    "path": "MedicationRequest.dosageInstruction.additionalInstruction.coding.code",
                    "min": 1,
                    "base": {"path": "Coding.code", "min": 0, "max": "1"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dosageInstruction.additionalInstruction.coding:snomedCT.display": (
                {
                    "id": "MedicationRequest.dosageInstruction.additionalInstruction.coding:snomedCT.display",
                    "extension": [
                        {
                            "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-translatable",
                            "valueBoolean": True,
                        }
                    ],
                    "path": "MedicationRequest.dosageInstruction.additionalInstruction.coding.display",
                    "min": 1,
                    "base": {"path": "Coding.display", "min": 0, "max": "1"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dosageInstruction.route.coding": (
                {
                    "id": "MedicationRequest.dosageInstruction.route.coding",
                    "path": "MedicationRequest.dosageInstruction.route.coding",
                    "slicing": {
                        "discriminator": [{"type": "value", "path": "system"}],
                        "ordered": False,
                        "rules": "open",
                    },
                    "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dosageInstruction.route.coding:snomedCT": (
                {
                    "id": "MedicationRequest.dosageInstruction.route.coding:snomedCT",
                    "path": "MedicationRequest.dosageInstruction.route.coding",
                    "sliceName": "snomedCT",
                    "max": "1",
                    "binding": {
                        "strength": "preferred",
                        "description": "A code from the SNOMED Clinical Terminology UK coding system that describes the e-Prescribing route of administration.",
                        "valueSetReference": {
                            "reference": "https://fhir.hl7.org.uk/STU3/ValueSet/CareConnect-MedicationDosageRoute-1"
                        },
                    },
                    "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dosageInstruction.route.coding:snomedCT.extension": (
                {
                    "id": "MedicationRequest.dosageInstruction.route.coding:snomedCT.extension",
                    "path": "MedicationRequest.dosageInstruction.route.coding.extension",
                    "slicing": {
                        "discriminator": [{"type": "value", "path": "url"}],
                        "rules": "open",
                    },
                    "base": {"path": "Element.extension", "min": 0, "max": "*"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dosageInstruction.route.coding:snomedCT.extension:snomedCTDescriptionID": (
                {
                    "id": "MedicationRequest.dosageInstruction.route.coding:snomedCT.extension:snomedCTDescriptionID",
                    "path": "MedicationRequest.dosageInstruction.route.coding.extension",
                    "sliceName": "snomedCTDescriptionID",
                    "type": [
                        {
                            "code": "Extension",
                            "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-coding-sctdescid",
                        }
                    ],
                    "base": {"path": "Element.extension", "min": 0, "max": "*"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dosageInstruction.route.coding:snomedCT.system": (
                {
                    "id": "MedicationRequest.dosageInstruction.route.coding:snomedCT.system",
                    "path": "MedicationRequest.dosageInstruction.route.coding.system",
                    "min": 1,
                    "fixedUri": "http://snomed.info/sct",
                    "base": {"path": "Coding.system", "min": 0, "max": "1"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dosageInstruction.route.coding:snomedCT.code": (
                {
                    "id": "MedicationRequest.dosageInstruction.route.coding:snomedCT.code",
                    "path": "MedicationRequest.dosageInstruction.route.coding.code",
                    "min": 1,
                    "base": {"path": "Coding.code", "min": 0, "max": "1"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dosageInstruction.route.coding:snomedCT.display": (
                {
                    "id": "MedicationRequest.dosageInstruction.route.coding:snomedCT.display",
                    "extension": [
                        {
                            "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-translatable",
                            "valueBoolean": True,
                        }
                    ],
                    "path": "MedicationRequest.dosageInstruction.route.coding.display",
                    "min": 1,
                    "base": {"path": "Coding.display", "min": 0, "max": "1"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dispenseRequest.quantity.extension": (
                {
                    "id": "MedicationRequest.dispenseRequest.quantity.extension",
                    "path": "MedicationRequest.dispenseRequest.quantity.extension",
                    "slicing": {
                        "discriminator": [{"type": "value", "path": "url"}],
                        "rules": "open",
                    },
                    "base": {"path": "Element.extension", "min": 0, "max": "*"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dispenseRequest.quantity.extension:quantityText": (
                {
                    "id": "MedicationRequest.dispenseRequest.quantity.extension:quantityText",
                    "path": "MedicationRequest.dispenseRequest.quantity.extension",
                    "sliceName": "quantityText",
                    "max": "1",
                    "type": [
                        {
                            "code": "Extension",
                            "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-CareConnect-MedicationQuantityText-1",
                        }
                    ],
                    "base": {"path": "Element.extension", "min": 0, "max": "*"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dispenseRequest.expectedSupplyDuration.value": (
                {
                    "id": "MedicationRequest.dispenseRequest.expectedSupplyDuration.value",
                    "path": "MedicationRequest.dispenseRequest.expectedSupplyDuration.value",
                    "min": 1,
                    "base": {"path": "Quantity.value", "min": 0, "max": "1"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dispenseRequest.expectedSupplyDuration.system": (
                {
                    "id": "MedicationRequest.dispenseRequest.expectedSupplyDuration.system",
                    "path": "MedicationRequest.dispenseRequest.expectedSupplyDuration.system",
                    "min": 1,
                    "fixedUri": "http://unitsofmeasure.org",
                    "base": {"path": "Quantity.system", "min": 0, "max": "1"},
                },
                {},
            )
        },
        {
            "MedicationRequest.dispenseRequest.expectedSupplyDuration.code": (
                {
                    "id": "MedicationRequest.dispenseRequest.expectedSupplyDuration.code",
                    "path": "MedicationRequest.dispenseRequest.expectedSupplyDuration.code",
                    "min": 1,
                    "binding": {
                        "strength": "required",
                        "description": "A unit of time (units from UCUM).",
                        "valueSetReference": {
                            "reference": "http://hl7.org/fhir/ValueSet/units-of-time"
                        },
                    },
                    "base": {"path": "Quantity.code", "min": 0, "max": "1"},
                },
                {},
            )
        },
        {
            "MedicationRequest.extension:medicationRepeatInformation": (
                {},
                {
                    "id": "MedicationRequest.extension:medicationRepeatInformation",
                    "path": "MedicationRequest.extension",
                    "sliceName": "medicationRepeatInformation",
                    "type": [
                        {
                            "code": "Extension",
                            "profile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-MedicationRepeatInformation"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.category": (
                {},
                {
                    "id": "MedicationRequest.category",
                    "path": "MedicationRequest.category",
                    "binding": {
                        "strength": "extensible",
                        "valueSet": "https://fhir.hl7.org.uk/ValueSet/UKCore-MedicationRequestCategory",
                    },
                },
            )
        },
        {
            "MedicationRequest.reported[x]": (
                {},
                {
                    "id": "MedicationRequest.reported[x]",
                    "path": "MedicationRequest.reported[x]",
                    "type": [
                        {"code": "boolean"},
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Patient",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Practitioner",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-PractitionerRole",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-RelatedPerson",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization",
                            ],
                        },
                    ],
                },
            )
        },
        {
            "MedicationRequest.medication[x]": (
                {},
                {
                    "id": "MedicationRequest.medication[x]",
                    "path": "MedicationRequest.medication[x]",
                    "type": [
                        {"code": "CodeableConcept"},
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Medication"
                            ],
                        },
                    ],
                    "binding": {
                        "strength": "extensible",
                        "valueSet": "https://fhir.hl7.org.uk/ValueSet/UKCore-MedicationCode",
                    },
                },
            )
        },
        {
            "MedicationRequest.subject.identifier.assigner": (
                {},
                {
                    "id": "MedicationRequest.subject.identifier.assigner",
                    "path": "MedicationRequest.subject.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.encounter": (
                {},
                {
                    "id": "MedicationRequest.encounter",
                    "path": "MedicationRequest.encounter",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Encounter"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.encounter.identifier.assigner": (
                {},
                {
                    "id": "MedicationRequest.encounter.identifier.assigner",
                    "path": "MedicationRequest.encounter.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.supportingInformation.identifier.assigner": (
                {},
                {
                    "id": "MedicationRequest.supportingInformation.identifier.assigner",
                    "path": "MedicationRequest.supportingInformation.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.requester": (
                {},
                {
                    "id": "MedicationRequest.requester",
                    "path": "MedicationRequest.requester",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Device",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Practitioner",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-PractitionerRole",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Patient",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-RelatedPerson",
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.requester.identifier.assigner": (
                {},
                {
                    "id": "MedicationRequest.requester.identifier.assigner",
                    "path": "MedicationRequest.requester.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.performer": (
                {},
                {
                    "id": "MedicationRequest.performer",
                    "path": "MedicationRequest.performer",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Device",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Practitioner",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-PractitionerRole",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Patient",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-RelatedPerson",
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-CareTeam",
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.performer.identifier.assigner": (
                {},
                {
                    "id": "MedicationRequest.performer.identifier.assigner",
                    "path": "MedicationRequest.performer.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.recorder.identifier.assigner": (
                {},
                {
                    "id": "MedicationRequest.recorder.identifier.assigner",
                    "path": "MedicationRequest.recorder.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.reasonReference.identifier.assigner": (
                {},
                {
                    "id": "MedicationRequest.reasonReference.identifier.assigner",
                    "path": "MedicationRequest.reasonReference.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.basedOn.identifier.assigner": (
                {},
                {
                    "id": "MedicationRequest.basedOn.identifier.assigner",
                    "path": "MedicationRequest.basedOn.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.courseOfTherapyType": (
                {},
                {
                    "id": "MedicationRequest.courseOfTherapyType",
                    "path": "MedicationRequest.courseOfTherapyType",
                    "short": "A course of therapy for a medication request",
                    "definition": "The description of the course of therapy for a medication request.",
                    "binding": {
                        "strength": "extensible",
                        "valueSet": "https://fhir.hl7.org.uk/ValueSet/UKCore-MedicationRequestCourseOfTherapy",
                    },
                },
            )
        },
        {
            "MedicationRequest.insurance.identifier.assigner": (
                {},
                {
                    "id": "MedicationRequest.insurance.identifier.assigner",
                    "path": "MedicationRequest.insurance.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.dosageInstruction.asNeeded[x]": (
                {},
                {
                    "id": "MedicationRequest.dosageInstruction.asNeeded[x]",
                    "path": "MedicationRequest.dosageInstruction.asNeeded[x]",
                    "binding": {
                        "strength": "extensible",
                        "valueSet": "https://fhir.hl7.org.uk/ValueSet/UKCore-MedicationPrecondition",
                    },
                },
            )
        },
        {
            "MedicationRequest.dosageInstruction.site": (
                {},
                {
                    "id": "MedicationRequest.dosageInstruction.site",
                    "path": "MedicationRequest.dosageInstruction.site",
                    "binding": {
                        "strength": "extensible",
                        "valueSet": "https://fhir.hl7.org.uk/ValueSet/UKCore-BodySite",
                    },
                },
            )
        },
        {
            "MedicationRequest.dosageInstruction.route": (
                {},
                {
                    "id": "MedicationRequest.dosageInstruction.route",
                    "path": "MedicationRequest.dosageInstruction.route",
                    "binding": {
                        "strength": "extensible",
                        "valueSet": "https://fhir.hl7.org.uk/ValueSet/UKCore-SubstanceOrProductAdministrationRoute",
                    },
                },
            )
        },
        {
            "MedicationRequest.dosageInstruction.method": (
                {},
                {
                    "id": "MedicationRequest.dosageInstruction.method",
                    "path": "MedicationRequest.dosageInstruction.method",
                    "binding": {
                        "strength": "extensible",
                        "valueSet": "https://fhir.hl7.org.uk/ValueSet/UKCore-MedicationDosageMethod",
                    },
                },
            )
        },
        {
            "MedicationRequest.dispenseRequest.performer.identifier.assigner": (
                {},
                {
                    "id": "MedicationRequest.dispenseRequest.performer.identifier.assigner",
                    "path": "MedicationRequest.dispenseRequest.performer.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.substitution": (
                {},
                {
                    "id": "MedicationRequest.substitution",
                    "path": "MedicationRequest.substitution",
                    "min": 1,
                },
            )
        },
        {
            "MedicationRequest.substitution.allowed[x]": (
                {},
                {
                    "id": "MedicationRequest.substitution.allowed[x]",
                    "path": "MedicationRequest.substitution.allowed[x]",
                    "definition": "The purpose of this element is to allow the prescriber to dispense a different drug from what was prescribed.",
                },
            )
        },
        {
            "MedicationRequest.priorPrescription.identifier.assigner": (
                {},
                {
                    "id": "MedicationRequest.priorPrescription.identifier.assigner",
                    "path": "MedicationRequest.priorPrescription.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.detectedIssue.identifier.assigner": (
                {},
                {
                    "id": "MedicationRequest.detectedIssue.identifier.assigner",
                    "path": "MedicationRequest.detectedIssue.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
        {
            "MedicationRequest.eventHistory.identifier.assigner": (
                {},
                {
                    "id": "MedicationRequest.eventHistory.identifier.assigner",
                    "path": "MedicationRequest.eventHistory.identifier.assigner",
                    "type": [
                        {
                            "code": "Reference",
                            "targetProfile": [
                                "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Organization"
                            ],
                        }
                    ],
                },
            )
        },
    ]

el_table = [
    {
        "AllergyIntolerance.extension": (
            {
                "id": "AllergyIntolerance.extension",
                "path": "AllergyIntolerance.extension",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "url"}],
                    "rules": "open",
                },
                "base": {"path": "DomainResource.extension", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.extension",
                "path": "AllergyIntolerance.extension",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "url"}],
                    "rules": "open",
                },
                "base": {"path": "DomainResource.extension", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.extension:encounter": (
            {
                "id": "AllergyIntolerance.extension:encounter",
                "path": "AllergyIntolerance.extension",
                "sliceName": "encounter",
                "max": "1",
                "type": [
                    {
                        "code": "Extension",
                        "profile": "http://hl7.org/fhir/StructureDefinition/encounter-associatedEncounter",
                    }
                ],
                "base": {"path": "DomainResource.extension", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.extension:encounter",
                "path": "AllergyIntolerance.extension",
                "sliceName": "encounter",
                "max": "1",
                "type": [
                    {
                        "code": "Extension",
                        "profile": "http://hl7.org/fhir/StructureDefinition/encounter-associatedEncounter",
                    }
                ],
                "mustSupport": True,
                "base": {"path": "DomainResource.extension", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.extension:allergyEnd": (
            {
                "id": "AllergyIntolerance.extension:allergyEnd",
                "path": "AllergyIntolerance.extension",
                "sliceName": "allergyEnd",
                "max": "1",
                "type": [
                    {
                        "code": "Extension",
                        "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-CareConnect-AllergyIntoleranceEnd-1",
                    }
                ],
                "base": {"path": "DomainResource.extension", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.extension:allergyEnd",
                "path": "AllergyIntolerance.extension",
                "sliceName": "allergyEnd",
                "max": "1",
                "type": [
                    {
                        "code": "Extension",
                        "profile": "https://fhir.nhs.uk/STU3/StructureDefinition/Extension-CareConnect-GPC-AllergyIntoleranceEnd-1",
                    }
                ],
                "mustSupport": True,
                "base": {"path": "DomainResource.extension", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.extension:evidence": (
            {
                "id": "AllergyIntolerance.extension:evidence",
                "path": "AllergyIntolerance.extension",
                "sliceName": "evidence",
                "max": "1",
                "type": [
                    {
                        "code": "Extension",
                        "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-CareConnect-Evidence-1",
                    }
                ],
                "base": {"path": "DomainResource.extension", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.extension:evidence",
                "path": "AllergyIntolerance.extension",
                "sliceName": "evidence",
                "max": "1",
                "type": [
                    {
                        "code": "Extension",
                        "profile": "https://fhir.nhs.uk/STU3/StructureDefinition/Extension-CareConnect-GPC-Evidence-1",
                    }
                ],
                "base": {"path": "DomainResource.extension", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.identifier.system": (
            {
                "id": "AllergyIntolerance.identifier.system",
                "path": "AllergyIntolerance.identifier.system",
                "min": 1,
                "base": {"path": "Identifier.system", "min": 0, "max": "1"},
            },
            {
                "id": "AllergyIntolerance.identifier.system",
                "path": "AllergyIntolerance.identifier.system",
                "min": 1,
                "base": {"path": "Identifier.system", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.identifier.value": (
            {
                "id": "AllergyIntolerance.identifier.value",
                "path": "AllergyIntolerance.identifier.value",
                "min": 1,
                "base": {"path": "Identifier.value", "min": 0, "max": "1"},
            },
            {
                "id": "AllergyIntolerance.identifier.value",
                "path": "AllergyIntolerance.identifier.value",
                "min": 1,
                "base": {"path": "Identifier.value", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.verificationStatus": (
            {
                "id": "AllergyIntolerance.verificationStatus",
                "path": "AllergyIntolerance.verificationStatus",
                "short": "unconfirmed | confirmed",
                "binding": {
                    "extension": [
                        {
                            "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-bindingName",
                            "valueString": "AllergyIntoleranceVerificationStatus",
                        }
                    ],
                    "strength": "required",
                    "valueSetReference": {
                        "reference": "https://fhir.hl7.org.uk/STU3/ValueSet/CareConnect-AllergyVerificationStatus-1"
                    },
                },
                "base": {
                    "path": "AllergyIntolerance.verificationStatus",
                    "min": 1,
                    "max": "1",
                },
            },
            {
                "id": "AllergyIntolerance.verificationStatus",
                "path": "AllergyIntolerance.verificationStatus",
                "short": "unconfirmed | confirmed",
                "fixedCode": "unconfirmed",
                "base": {
                    "path": "AllergyIntolerance.verificationStatus",
                    "min": 1,
                    "max": "1",
                },
            },
        )
    },
    {
        "AllergyIntolerance.patient": (
            {
                "id": "AllergyIntolerance.patient",
                "path": "AllergyIntolerance.patient",
                "type": [
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Patient-1",
                    }
                ],
                "base": {"path": "AllergyIntolerance.patient", "min": 1, "max": "1"},
            },
            {
                "id": "AllergyIntolerance.patient",
                "path": "AllergyIntolerance.patient",
                "type": [
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.nhs.uk/STU3/StructureDefinition/CareConnect-GPC-Patient-1",
                    }
                ],
                "base": {"path": "AllergyIntolerance.patient", "min": 1, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.onset[x]": (
            {
                "id": "AllergyIntolerance.onset[x]",
                "path": "AllergyIntolerance.onset[x]",
                "mustSupport": True,
                "base": {"path": "AllergyIntolerance.onset[x]", "min": 0, "max": "1"},
            },
            {
                "id": "AllergyIntolerance.onset[x]",
                "path": "AllergyIntolerance.onset[x]",
                "mustSupport": True,
                "base": {"path": "AllergyIntolerance.onset[x]", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.assertedDate": (
            {
                "id": "AllergyIntolerance.assertedDate",
                "path": "AllergyIntolerance.assertedDate",
                "min": 1,
                "base": {
                    "path": "AllergyIntolerance.assertedDate",
                    "min": 0,
                    "max": "1",
                },
            },
            {
                "id": "AllergyIntolerance.assertedDate",
                "path": "AllergyIntolerance.assertedDate",
                "min": 1,
                "base": {
                    "path": "AllergyIntolerance.assertedDate",
                    "min": 0,
                    "max": "1",
                },
            },
        )
    },
    {
        "AllergyIntolerance.recorder": (
            {
                "id": "AllergyIntolerance.recorder",
                "path": "AllergyIntolerance.recorder",
                "type": [
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Patient-1",
                    },
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Practitioner-1",
                    },
                ],
                "base": {"path": "AllergyIntolerance.recorder", "min": 0, "max": "1"},
            },
            {
                "id": "AllergyIntolerance.recorder",
                "path": "AllergyIntolerance.recorder",
                "min": 1,
                "type": [
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.nhs.uk/STU3/StructureDefinition/CareConnect-GPC-Patient-1",
                    },
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.nhs.uk/STU3/StructureDefinition/CareConnect-GPC-Practitioner-1",
                    },
                ],
                "base": {"path": "AllergyIntolerance.recorder", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.asserter": (
            {
                "id": "AllergyIntolerance.asserter",
                "path": "AllergyIntolerance.asserter",
                "type": [
                    {
                        "code": "Reference",
                        "targetProfile": "http://hl7.org/fhir/StructureDefinition/RelatedPerson",
                    },
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Patient-1",
                    },
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Practitioner-1",
                    },
                ],
                "base": {"path": "AllergyIntolerance.asserter", "min": 0, "max": "1"},
            },
            {
                "id": "AllergyIntolerance.asserter",
                "path": "AllergyIntolerance.asserter",
                "type": [
                    {
                        "code": "Reference",
                        "targetProfile": "http://hl7.org/fhir/StructureDefinition/RelatedPerson",
                    },
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.nhs.uk/STU3/StructureDefinition/CareConnect-GPC-Patient-1",
                    },
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.nhs.uk/STU3/StructureDefinition/CareConnect-GPC-Practitioner-1",
                    },
                ],
                "mustSupport": True,
                "base": {"path": "AllergyIntolerance.asserter", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.note.author[x]": (
            {
                "id": "AllergyIntolerance.note.author[x]",
                "path": "AllergyIntolerance.note.author[x]",
                "type": [
                    {
                        "code": "Reference",
                        "targetProfile": "http://hl7.org/fhir/StructureDefinition/RelatedPerson",
                    },
                    {"code": "string"},
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Patient-1",
                    },
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Practitioner-1",
                    },
                ],
                "base": {"path": "Annotation.author[x]", "min": 0, "max": "1"},
            },
            {
                "id": "AllergyIntolerance.note.author[x]",
                "path": "AllergyIntolerance.note.author[x]",
                "type": [
                    {
                        "code": "Reference",
                        "targetProfile": "http://hl7.org/fhir/StructureDefinition/RelatedPerson",
                    },
                    {"code": "string"},
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.nhs.uk/STU3/StructureDefinition/CareConnect-GPC-Patient-1",
                    },
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.nhs.uk/STU3/StructureDefinition/CareConnect-GPC-Practitioner-1",
                    },
                ],
                "base": {"path": "Annotation.author[x]", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.substance.coding": (
            {
                "id": "AllergyIntolerance.reaction.substance.coding",
                "path": "AllergyIntolerance.reaction.substance.coding",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "system"}],
                    "ordered": False,
                    "rules": "open",
                },
                "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.reaction.substance.coding",
                "path": "AllergyIntolerance.reaction.substance.coding",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "system"}],
                    "ordered": False,
                    "rules": "open",
                },
                "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.substance.coding:snomedCT": (
            {
                "id": "AllergyIntolerance.reaction.substance.coding:snomedCT",
                "path": "AllergyIntolerance.reaction.substance.coding",
                "sliceName": "snomedCT",
                "max": "1",
                "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.reaction.substance.coding:snomedCT",
                "path": "AllergyIntolerance.reaction.substance.coding",
                "sliceName": "snomedCT",
                "max": "1",
                "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.substance.coding:snomedCT.extension": (
            {
                "id": "AllergyIntolerance.reaction.substance.coding:snomedCT.extension",
                "path": "AllergyIntolerance.reaction.substance.coding.extension",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "url"}],
                    "rules": "open",
                },
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.reaction.substance.coding:snomedCT.extension",
                "path": "AllergyIntolerance.reaction.substance.coding.extension",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "url"}],
                    "rules": "open",
                },
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.substance.coding:snomedCT.extension:snomedCTDescriptionID": (
            {
                "id": "AllergyIntolerance.reaction.substance.coding:snomedCT.extension:snomedCTDescriptionID",
                "path": "AllergyIntolerance.reaction.substance.coding.extension",
                "sliceName": "snomedCTDescriptionID",
                "type": [
                    {
                        "code": "Extension",
                        "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-coding-sctdescid",
                    }
                ],
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.reaction.substance.coding:snomedCT.extension:snomedCTDescriptionID",
                "path": "AllergyIntolerance.reaction.substance.coding.extension",
                "sliceName": "snomedCTDescriptionID",
                "type": [
                    {
                        "code": "Extension",
                        "profile": "https://fhir.nhs.uk/STU3/StructureDefinition/Extension-coding-sctdescid",
                    }
                ],
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.substance.coding:snomedCT.system": (
            {
                "id": "AllergyIntolerance.reaction.substance.coding:snomedCT.system",
                "path": "AllergyIntolerance.reaction.substance.coding.system",
                "min": 1,
                "fixedUri": "http://snomed.info/sct",
                "base": {"path": "Coding.system", "min": 0, "max": "1"},
            },
            {
                "id": "AllergyIntolerance.reaction.substance.coding:snomedCT.system",
                "path": "AllergyIntolerance.reaction.substance.coding.system",
                "min": 1,
                "fixedUri": "http://snomed.info/sct",
                "base": {"path": "Coding.system", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.substance.coding:snomedCT.code": (
            {
                "id": "AllergyIntolerance.reaction.substance.coding:snomedCT.code",
                "path": "AllergyIntolerance.reaction.substance.coding.code",
                "min": 1,
                "base": {"path": "Coding.code", "min": 0, "max": "1"},
            },
            {
                "id": "AllergyIntolerance.reaction.substance.coding:snomedCT.code",
                "path": "AllergyIntolerance.reaction.substance.coding.code",
                "min": 1,
                "base": {"path": "Coding.code", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.manifestation": (
            {
                "id": "AllergyIntolerance.reaction.manifestation",
                "path": "AllergyIntolerance.reaction.manifestation",
                "binding": {
                    "extension": [
                        {
                            "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-bindingName",
                            "valueString": "Manifestation",
                        }
                    ],
                    "strength": "extensible",
                    "valueSetReference": {
                        "reference": "https://fhir.hl7.org.uk/STU3/ValueSet/CareConnect-AllergyManifestation-1"
                    },
                },
                "base": {
                    "path": "AllergyIntolerance.reaction.manifestation",
                    "min": 1,
                    "max": "*",
                },
            },
            {
                "id": "AllergyIntolerance.reaction.manifestation",
                "path": "AllergyIntolerance.reaction.manifestation",
                "binding": {
                    "extension": [
                        {
                            "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-bindingName",
                            "valueString": "Manifestation",
                        }
                    ],
                    "strength": "extensible",
                    "valueSetReference": {
                        "reference": "https://fhir.hl7.org.uk/STU3/ValueSet/CareConnect-AllergyManifestation-1"
                    },
                },
                "base": {
                    "path": "AllergyIntolerance.reaction.manifestation",
                    "min": 1,
                    "max": "*",
                },
            },
        )
    },
    {
        "AllergyIntolerance.reaction.manifestation.coding": (
            {
                "id": "AllergyIntolerance.reaction.manifestation.coding",
                "path": "AllergyIntolerance.reaction.manifestation.coding",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "system"}],
                    "ordered": False,
                    "rules": "open",
                },
                "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.reaction.manifestation.coding",
                "path": "AllergyIntolerance.reaction.manifestation.coding",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "system"}],
                    "ordered": False,
                    "rules": "open",
                },
                "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.manifestation.coding:snomedCT": (
            {
                "id": "AllergyIntolerance.reaction.manifestation.coding:snomedCT",
                "path": "AllergyIntolerance.reaction.manifestation.coding",
                "sliceName": "snomedCT",
                "max": "1",
                "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.reaction.manifestation.coding:snomedCT",
                "path": "AllergyIntolerance.reaction.manifestation.coding",
                "sliceName": "snomedCT",
                "max": "1",
                "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.manifestation.coding:snomedCT.extension": (
            {
                "id": "AllergyIntolerance.reaction.manifestation.coding:snomedCT.extension",
                "path": "AllergyIntolerance.reaction.manifestation.coding.extension",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "url"}],
                    "rules": "open",
                },
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.reaction.manifestation.coding:snomedCT.extension",
                "path": "AllergyIntolerance.reaction.manifestation.coding.extension",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "url"}],
                    "rules": "open",
                },
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.manifestation.coding:snomedCT.extension:snomedCTDescriptionID": (
            {
                "id": "AllergyIntolerance.reaction.manifestation.coding:snomedCT.extension:snomedCTDescriptionID",
                "path": "AllergyIntolerance.reaction.manifestation.coding.extension",
                "sliceName": "snomedCTDescriptionID",
                "type": [
                    {
                        "code": "Extension",
                        "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-coding-sctdescid",
                    }
                ],
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.reaction.manifestation.coding:snomedCT.extension:snomedCTDescriptionID",
                "path": "AllergyIntolerance.reaction.manifestation.coding.extension",
                "sliceName": "snomedCTDescriptionID",
                "type": [
                    {
                        "code": "Extension",
                        "profile": "https://fhir.nhs.uk/STU3/StructureDefinition/Extension-coding-sctdescid",
                    }
                ],
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.manifestation.coding:snomedCT.system": (
            {
                "id": "AllergyIntolerance.reaction.manifestation.coding:snomedCT.system",
                "path": "AllergyIntolerance.reaction.manifestation.coding.system",
                "min": 1,
                "fixedUri": "http://snomed.info/sct",
                "base": {"path": "Coding.system", "min": 0, "max": "1"},
            },
            {
                "id": "AllergyIntolerance.reaction.manifestation.coding:snomedCT.system",
                "path": "AllergyIntolerance.reaction.manifestation.coding.system",
                "min": 1,
                "fixedUri": "http://snomed.info/sct",
                "base": {"path": "Coding.system", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.manifestation.coding:snomedCT.code": (
            {
                "id": "AllergyIntolerance.reaction.manifestation.coding:snomedCT.code",
                "path": "AllergyIntolerance.reaction.manifestation.coding.code",
                "min": 1,
                "base": {"path": "Coding.code", "min": 0, "max": "1"},
            },
            {
                "id": "AllergyIntolerance.reaction.manifestation.coding:snomedCT.code",
                "path": "AllergyIntolerance.reaction.manifestation.coding.code",
                "min": 1,
                "base": {"path": "Coding.code", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.severity": (
            {
                "id": "AllergyIntolerance.reaction.severity",
                "path": "AllergyIntolerance.reaction.severity",
                "binding": {
                    "extension": [
                        {
                            "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-bindingName",
                            "valueString": "AllergyIntoleranceSeverity",
                        }
                    ],
                    "strength": "required",
                    "valueSetReference": {
                        "reference": "https://fhir.hl7.org.uk/STU3/ValueSet/CareConnect-ReactionEventSeverity-1"
                    },
                },
                "base": {
                    "path": "AllergyIntolerance.reaction.severity",
                    "min": 0,
                    "max": "1",
                },
            },
            {
                "id": "AllergyIntolerance.reaction.severity",
                "path": "AllergyIntolerance.reaction.severity",
                "mustSupport": True,
                "base": {
                    "path": "AllergyIntolerance.reaction.severity",
                    "min": 0,
                    "max": "1",
                },
            },
        )
    },
    {
        "AllergyIntolerance.reaction.exposureRoute": (
            {
                "id": "AllergyIntolerance.reaction.exposureRoute",
                "path": "AllergyIntolerance.reaction.exposureRoute",
                "binding": {
                    "extension": [
                        {
                            "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-bindingName",
                            "valueString": "RouteOfAdministration",
                        }
                    ],
                    "strength": "example",
                    "valueSetReference": {
                        "reference": "https://fhir.hl7.org.uk/STU3/ValueSet/CareConnect-AllergyExposureRoute-1"
                    },
                },
                "base": {
                    "path": "AllergyIntolerance.reaction.exposureRoute",
                    "min": 0,
                    "max": "1",
                },
            },
            {
                "id": "AllergyIntolerance.reaction.exposureRoute",
                "path": "AllergyIntolerance.reaction.exposureRoute",
                "binding": {
                    "extension": [
                        {
                            "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-bindingName",
                            "valueString": "RouteOfAdministration",
                        }
                    ],
                    "strength": "example",
                    "valueSetReference": {
                        "reference": "https://fhir.nhs.uk/STU3/ValueSet/CareConnect-AllergyExposureRoute-1"
                    },
                },
                "base": {
                    "path": "AllergyIntolerance.reaction.exposureRoute",
                    "min": 0,
                    "max": "1",
                },
            },
        )
    },
    {
        "AllergyIntolerance.reaction.exposureRoute.coding": (
            {
                "id": "AllergyIntolerance.reaction.exposureRoute.coding",
                "path": "AllergyIntolerance.reaction.exposureRoute.coding",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "system"}],
                    "ordered": False,
                    "rules": "open",
                },
                "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.reaction.exposureRoute.coding",
                "path": "AllergyIntolerance.reaction.exposureRoute.coding",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "system"}],
                    "ordered": False,
                    "rules": "open",
                },
                "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT": (
            {
                "id": "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT",
                "path": "AllergyIntolerance.reaction.exposureRoute.coding",
                "sliceName": "snomedCT",
                "max": "1",
                "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT",
                "path": "AllergyIntolerance.reaction.exposureRoute.coding",
                "sliceName": "snomedCT",
                "max": "1",
                "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.extension": (
            {
                "id": "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.extension",
                "path": "AllergyIntolerance.reaction.exposureRoute.coding.extension",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "url"}],
                    "rules": "open",
                },
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.extension",
                "path": "AllergyIntolerance.reaction.exposureRoute.coding.extension",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "url"}],
                    "rules": "open",
                },
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.extension:snomedCTDescriptionID": (
            {
                "id": "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.extension:snomedCTDescriptionID",
                "path": "AllergyIntolerance.reaction.exposureRoute.coding.extension",
                "sliceName": "snomedCTDescriptionID",
                "type": [
                    {
                        "code": "Extension",
                        "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-coding-sctdescid",
                    }
                ],
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
            {
                "id": "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.extension:snomedCTDescriptionID",
                "path": "AllergyIntolerance.reaction.exposureRoute.coding.extension",
                "sliceName": "snomedCTDescriptionID",
                "type": [
                    {
                        "code": "Extension",
                        "profile": "https://fhir.nhs.uk/STU3/StructureDefinition/Extension-coding-sctdescid",
                    }
                ],
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.system": (
            {
                "id": "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.system",
                "path": "AllergyIntolerance.reaction.exposureRoute.coding.system",
                "min": 1,
                "fixedUri": "http://snomed.info/sct",
                "base": {"path": "Coding.system", "min": 0, "max": "1"},
            },
            {
                "id": "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.system",
                "path": "AllergyIntolerance.reaction.exposureRoute.coding.system",
                "min": 1,
                "fixedUri": "http://snomed.info/sct",
                "base": {"path": "Coding.system", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.code": (
            {
                "id": "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.code",
                "path": "AllergyIntolerance.reaction.exposureRoute.coding.code",
                "min": 1,
                "base": {"path": "Coding.code", "min": 0, "max": "1"},
            },
            {
                "id": "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.code",
                "path": "AllergyIntolerance.reaction.exposureRoute.coding.code",
                "min": 1,
                "base": {"path": "Coding.code", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.note.author[x]": (
            {
                "id": "AllergyIntolerance.reaction.note.author[x]",
                "path": "AllergyIntolerance.reaction.note.author[x]",
                "type": [
                    {
                        "code": "Reference",
                        "targetProfile": "http://hl7.org/fhir/StructureDefinition/RelatedPerson",
                    },
                    {"code": "string"},
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Patient-1",
                    },
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Practitioner-1",
                    },
                ],
                "base": {"path": "Annotation.author[x]", "min": 0, "max": "1"},
            },
            {
                "id": "AllergyIntolerance.reaction.note.author[x]",
                "path": "AllergyIntolerance.reaction.note.author[x]",
                "type": [
                    {
                        "code": "Reference",
                        "targetProfile": "http://hl7.org/fhir/StructureDefinition/RelatedPerson",
                    },
                    {"code": "string"},
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.nhs.uk/STU3/StructureDefinition/CareConnect-GPC-Patient-1",
                    },
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.nhs.uk/STU3/StructureDefinition/CareConnect-GPC-Practitioner-1",
                    },
                ],
                "base": {"path": "Annotation.author[x]", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.identifier.assigner": (
            {
                "id": "AllergyIntolerance.identifier.assigner",
                "path": "AllergyIntolerance.identifier.assigner",
                "type": [
                    {
                        "code": "Reference",
                        "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Organization-1",
                    }
                ],
                "base": {"path": "Identifier.assigner", "min": 0, "max": "1"},
            },
            {},
        )
    },
    {
        "AllergyIntolerance.code.coding": (
            {
                "id": "AllergyIntolerance.code.coding",
                "path": "AllergyIntolerance.code.coding",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "system"}],
                    "rules": "open",
                },
                "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
            },
            {},
        )
    },
    {
        "AllergyIntolerance.code.coding:snomedCT": (
            {
                "id": "AllergyIntolerance.code.coding:snomedCT",
                "path": "AllergyIntolerance.code.coding",
                "sliceName": "snomedCT",
                "max": "1",
                "binding": {
                    "strength": "example",
                    "description": "A code from the SNOMED Clinical Terminology UK or a code from the v3 Code System NullFlavor specifying why a valid value is not present.",
                    "valueSetReference": {
                        "reference": "https://fhir.hl7.org.uk/STU3/ValueSet/CareConnect-AllergyCode-1"
                    },
                },
                "base": {"path": "CodeableConcept.coding", "min": 0, "max": "*"},
            },
            {},
        )
    },
    {
        "AllergyIntolerance.code.coding:snomedCT.extension": (
            {
                "id": "AllergyIntolerance.code.coding:snomedCT.extension",
                "path": "AllergyIntolerance.code.coding.extension",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "url"}],
                    "rules": "open",
                },
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
            {},
        )
    },
    {
        "AllergyIntolerance.code.coding:snomedCT.extension:snomedCTDescriptionID": (
            {
                "id": "AllergyIntolerance.code.coding:snomedCT.extension:snomedCTDescriptionID",
                "path": "AllergyIntolerance.code.coding.extension",
                "sliceName": "snomedCTDescriptionID",
                "type": [
                    {
                        "code": "Extension",
                        "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-coding-sctdescid",
                    }
                ],
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
            {},
        )
    },
    {
        "AllergyIntolerance.code.coding:snomedCT.system": (
            {
                "id": "AllergyIntolerance.code.coding:snomedCT.system",
                "path": "AllergyIntolerance.code.coding.system",
                "min": 1,
                "base": {"path": "Coding.system", "min": 0, "max": "1"},
            },
            {},
        )
    },
    {
        "AllergyIntolerance.code.coding:snomedCT.code": (
            {
                "id": "AllergyIntolerance.code.coding:snomedCT.code",
                "path": "AllergyIntolerance.code.coding.code",
                "min": 1,
                "base": {"path": "Coding.code", "min": 0, "max": "1"},
            },
            {},
        )
    },
    {
        "AllergyIntolerance.code.coding:snomedCT.display": (
            {
                "id": "AllergyIntolerance.code.coding:snomedCT.display",
                "extension": [
                    {
                        "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-translatable",
                        "valueBoolean": True,
                    }
                ],
                "path": "AllergyIntolerance.code.coding.display",
                "min": 1,
                "base": {"path": "Coding.display", "min": 0, "max": "1"},
            },
            {},
        )
    },
    {
        "AllergyIntolerance.reaction.substance.coding:snomedCT.display": (
            {
                "id": "AllergyIntolerance.reaction.substance.coding:snomedCT.display",
                "extension": [
                    {
                        "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-translatable",
                        "valueBoolean": True,
                    }
                ],
                "path": "AllergyIntolerance.reaction.substance.coding.display",
                "min": 1,
                "base": {"path": "Coding.display", "min": 0, "max": "1"},
            },
            {},
        )
    },
    {
        "AllergyIntolerance.reaction.manifestation.coding:snomedCT.display": (
            {
                "id": "AllergyIntolerance.reaction.manifestation.coding:snomedCT.display",
                "extension": [
                    {
                        "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-translatable",
                        "valueBoolean": True,
                    }
                ],
                "path": "AllergyIntolerance.reaction.manifestation.coding.display",
                "min": 1,
                "base": {"path": "Coding.display", "min": 0, "max": "1"},
            },
            {},
        )
    },
    {
        "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.display": (
            {
                "id": "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.display",
                "extension": [
                    {
                        "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-translatable",
                        "valueBoolean": True,
                    }
                ],
                "path": "AllergyIntolerance.reaction.exposureRoute.coding.display",
                "min": 1,
                "base": {"path": "Coding.display", "min": 0, "max": "1"},
            },
            {},
        )
    },
    {
        "AllergyIntolerance.meta.profile": (
            {},
            {
                "id": "AllergyIntolerance.meta.profile",
                "path": "AllergyIntolerance.meta.profile",
                "min": 1,
                "base": {"path": "Meta.profile", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.identifier": (
            {},
            {
                "id": "AllergyIntolerance.identifier",
                "path": "AllergyIntolerance.identifier",
                "min": 1,
                "base": {"path": "AllergyIntolerance.identifier", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.clinicalStatus": (
            {},
            {
                "id": "AllergyIntolerance.clinicalStatus",
                "path": "AllergyIntolerance.clinicalStatus",
                "min": 1,
                "base": {
                    "path": "AllergyIntolerance.clinicalStatus",
                    "min": 0,
                    "max": "1",
                },
            },
        )
    },
    {
        "AllergyIntolerance.category": (
            {},
            {
                "id": "AllergyIntolerance.category",
                "path": "AllergyIntolerance.category",
                "min": 1,
                "base": {"path": "AllergyIntolerance.category", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.code": (
            {},
            {
                "id": "AllergyIntolerance.code",
                "path": "AllergyIntolerance.code",
                "min": 1,
                "binding": {
                    "extension": [
                        {
                            "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-bindingName",
                            "valueString": "AllergyIntoleranceCode",
                        }
                    ],
                    "strength": "example",
                    "valueSetReference": {
                        "reference": "https://fhir.nhs.uk/STU3/ValueSet/CareConnect-AllergyCode-1"
                    },
                },
                "base": {"path": "AllergyIntolerance.code", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.code.coding.extension": (
            {},
            {
                "id": "AllergyIntolerance.code.coding.extension",
                "path": "AllergyIntolerance.code.coding.extension",
                "slicing": {
                    "discriminator": [{"type": "value", "path": "url"}],
                    "rules": "open",
                },
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.code.coding.extension:snomedCTDescriptionID": (
            {},
            {
                "id": "AllergyIntolerance.code.coding.extension:snomedCTDescriptionID",
                "path": "AllergyIntolerance.code.coding.extension",
                "sliceName": "snomedCTDescriptionID",
                "type": [
                    {
                        "code": "Extension",
                        "profile": "https://fhir.nhs.uk/STU3/StructureDefinition/Extension-coding-sctdescid",
                    }
                ],
                "base": {"path": "Element.extension", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.code.coding.system": (
            {},
            {
                "id": "AllergyIntolerance.code.coding.system",
                "path": "AllergyIntolerance.code.coding.system",
                "min": 1,
                "base": {"path": "Coding.system", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.code.coding.version": (
            {},
            {
                "id": "AllergyIntolerance.code.coding.version",
                "path": "AllergyIntolerance.code.coding.version",
                "max": "0",
                "base": {"path": "Coding.version", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.code.coding.code": (
            {},
            {
                "id": "AllergyIntolerance.code.coding.code",
                "path": "AllergyIntolerance.code.coding.code",
                "min": 1,
                "base": {"path": "Coding.code", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.note": (
            {},
            {
                "id": "AllergyIntolerance.note",
                "path": "AllergyIntolerance.note",
                "mustSupport": True,
                "base": {"path": "AllergyIntolerance.note", "min": 0, "max": "*"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.substance.coding:snomedCT.version": (
            {},
            {
                "id": "AllergyIntolerance.reaction.substance.coding:snomedCT.version",
                "path": "AllergyIntolerance.reaction.substance.coding.version",
                "max": "0",
                "base": {"path": "Coding.version", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.manifestation.coding:snomedCT.version": (
            {},
            {
                "id": "AllergyIntolerance.reaction.manifestation.coding:snomedCT.version",
                "path": "AllergyIntolerance.reaction.manifestation.coding.version",
                "max": "0",
                "base": {"path": "Coding.version", "min": 0, "max": "1"},
            },
        )
    },
    {
        "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.version": (
            {},
            {
                "id": "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.version",
                "path": "AllergyIntolerance.reaction.exposureRoute.coding.version",
                "max": "0",
                "base": {"path": "Coding.version", "min": 0, "max": "1"},
            },
        )
    },
]

com_res = {
    "AllergyIntolerance.extension": {
        "slicing": {
            "table_result": ("Match", "Match"),
            "match": '{\n  "discriminator": [\n    {\n      "path": "url",\n      "type": "value"\n    }\n  ],\n  "rules": "open"\n}',
            "component_diff": {},
            "base": '```json\n{\n  "description": "Extensions are always sliced by (at least) url",\n  "discriminator": [\n    {\n      "path": "url",\n      "type": "value"\n    }\n  ],\n  "rules": "open"\n}\n```',
        }
    },
    "AllergyIntolerance.extension:encounter": {
        "mustSupport": {
            "table_result": ("Not defined", True),
            "match": {},
            "component_diff": {},
            "base": '"mustSupport" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.extension:allergyEnd": {
        "mustSupport": {
            "table_result": ("Not defined", True),
            "match": {},
            "component_diff": {},
            "base": '"mustSupport" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.extension:evidence": {
        "type": {
            "table_result": ("See diff", "See diff"),
            "match": {},
            "component_diff": ' [  \n   {  \n     "code": "Extension",  \n-    "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-CareConnect-Evidence-1"  \n     "profile": "https://fhir.nhs.uk/STU3/StructureDefinition/Extension-CareConnect-GPC-Evidence-1"  \n   }  \n ]  \n',
            "base": '```json\n[\n  {\n    "code": "Extension"\n  }\n]\n```',
        }
    },
    "AllergyIntolerance.identifier.system": {
        "min": {
            "table_result": ('Match. "min" == 1', 'Match. "min" == 1'),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.identifier.value": {
        "min": {
            "table_result": ('Match. "min" == 1', 'Match. "min" == 1'),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.verificationStatus": {
        "fixedCode": {
            "table_result": ("Not defined", "unconfirmed"),
            "match": {},
            "component_diff": {},
            "base": '"fixedCode" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.patient": {
        "type": {
            "table_result": ("See diff", "See diff"),
            "match": {},
            "component_diff": ' [  \n   {  \n     "code": "Reference",  \n-    "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Patient-1"  \n     "targetProfile": "https://fhir.nhs.uk/STU3/StructureDefinition/CareConnect-GPC-Patient-1"  \n   }  \n ]  \n',
            "base": '```json\n[\n  {\n    "code": "Reference",\n    "targetProfile": "http://hl7.org/fhir/StructureDefinition/Patient"\n  }\n]\n```',
        }
    },
    "AllergyIntolerance.onset[x]": {
        "mustSupport": {
            "table_result": (
                'Match. "mustSupport" == True',
                'Match. "mustSupport" == True',
            ),
            "match": {},
            "component_diff": {},
            "base": '"mustSupport" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.assertedDate": {
        "min": {
            "table_result": ('Match. "min" == 1', 'Match. "min" == 1'),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.recorder": {
        "min": {
            "table_result": ("Not defined", 1),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.asserter": {
        "mustSupport": {
            "table_result": ("Not defined", True),
            "match": {},
            "component_diff": {},
            "base": '"mustSupport" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.note.author[x]": {
        "type": {
            "table_result": ("See diff", "See diff"),
            "match": {},
            "component_diff": ' [  \n   {  \n     "code": "Reference",  \n     "targetProfile": "http://hl7.org/fhir/StructureDefinition/RelatedPerson"  \n   },  \n   {  \n     "code": "string"  \n   },  \n   {  \n     "code": "Reference",  \n-    "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Patient-1"  \n     "targetProfile": "https://fhir.nhs.uk/STU3/StructureDefinition/CareConnect-GPC-Patient-1"  \n   },  \n   {  \n     "code": "Reference",  \n-    "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Practitioner-1"  \n     "targetProfile": "https://fhir.nhs.uk/STU3/StructureDefinition/CareConnect-GPC-Practitioner-1"  \n   }  \n ]  \n',
            "base": '```json\n[\n  {\n    "code": "Reference",\n    "targetProfile": "http://hl7.org/fhir/StructureDefinition/Practitioner"\n  },\n  {\n    "code": "Reference",\n    "targetProfile": "http://hl7.org/fhir/StructureDefinition/Patient"\n  },\n  {\n    "code": "Reference",\n    "targetProfile": "http://hl7.org/fhir/StructureDefinition/RelatedPerson"\n  },\n  {\n    "code": "string"\n  }\n]\n```',
        }
    },
    "AllergyIntolerance.reaction.substance.coding": {
        "slicing": {
            "table_result": ("Match", "Match"),
            "match": '{\n  "discriminator": [\n    {\n      "path": "system",\n      "type": "value"\n    }\n  ],\n  "ordered": false,\n  "rules": "open"\n}',
            "component_diff": {},
            "base": '"slicing" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.reaction.substance.coding:snomedCT": {
        "max": {
            "table_result": ('Match. "max" == 1', 'Match. "max" == 1'),
            "match": {},
            "component_diff": {},
            "base": '"max" == *',
        }
    },
    "AllergyIntolerance.reaction.substance.coding:snomedCT.extension": {
        "slicing": {
            "table_result": ("Match", "Match"),
            "match": '{\n  "discriminator": [\n    {\n      "path": "url",\n      "type": "value"\n    }\n  ],\n  "rules": "open"\n}',
            "component_diff": {},
            "base": '```json\n{\n  "description": "Extensions are always sliced by (at least) url",\n  "discriminator": [\n    {\n      "path": "url",\n      "type": "value"\n    }\n  ],\n  "rules": "open"\n}\n```',
        }
    },
    "AllergyIntolerance.reaction.substance.coding:snomedCT.extension:snomedCTDescriptionID": {
        "type": {
            "table_result": ("See diff", "See diff"),
            "match": {},
            "component_diff": ' [  \n   {  \n     "code": "Extension",  \n-    "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-coding-sctdescid"  \n     "profile": "https://fhir.nhs.uk/STU3/StructureDefinition/Extension-coding-sctdescid"  \n   }  \n ]  \n',
            "base": '```json\n[\n  {\n    "code": "Extension"\n  }\n]\n```',
        }
    },
    "AllergyIntolerance.reaction.substance.coding:snomedCT.system": {
        "fixedUri": {
            "table_result": (
                'Match. "fixedUri" == http://snomed.info/sct',
                'Match. "fixedUri" == http://snomed.info/sct',
            ),
            "match": {},
            "component_diff": {},
            "base": '"fixedUri" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.reaction.substance.coding:snomedCT.code": {
        "min": {
            "table_result": ('Match. "min" == 1', 'Match. "min" == 1'),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.reaction.manifestation": {
        "binding": {
            "table_result": ("Match", "Match"),
            "match": '{\n  "extension": [\n    {\n      "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-bindingName",\n      "valueString": "Manifestation"\n    }\n  ],\n  "strength": "extensible",\n  "valueSetReference": {\n    "reference": "https://fhir.hl7.org.uk/STU3/ValueSet/CareConnect-AllergyManifestation-1"\n  }\n}',
            "component_diff": {},
            "base": '```json\n{\n  "description": "Clinical symptoms and/or signs that are observed or associated with an Adverse Reaction Event.",\n  "extension": [\n    {\n      "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-bindingName",\n      "valueString": "Manifestation"\n    }\n  ],\n  "strength": "example",\n  "valueSetReference": {\n    "reference": "http://hl7.org/fhir/ValueSet/clinical-findings"\n  }\n}\n```',
        }
    },
    "AllergyIntolerance.reaction.manifestation.coding": {
        "slicing": {
            "table_result": ("Match", "Match"),
            "match": '{\n  "discriminator": [\n    {\n      "path": "system",\n      "type": "value"\n    }\n  ],\n  "ordered": false,\n  "rules": "open"\n}',
            "component_diff": {},
            "base": '"slicing" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.reaction.manifestation.coding:snomedCT": {
        "max": {
            "table_result": ('Match. "max" == 1', 'Match. "max" == 1'),
            "match": {},
            "component_diff": {},
            "base": '"max" == *',
        }
    },
    "AllergyIntolerance.reaction.manifestation.coding:snomedCT.extension": {
        "slicing": {
            "table_result": ("Match", "Match"),
            "match": '{\n  "discriminator": [\n    {\n      "path": "url",\n      "type": "value"\n    }\n  ],\n  "rules": "open"\n}',
            "component_diff": {},
            "base": '```json\n{\n  "description": "Extensions are always sliced by (at least) url",\n  "discriminator": [\n    {\n      "path": "url",\n      "type": "value"\n    }\n  ],\n  "rules": "open"\n}\n```',
        }
    },
    "AllergyIntolerance.reaction.manifestation.coding:snomedCT.extension:snomedCTDescriptionID": {
        "type": {
            "table_result": ("See diff", "See diff"),
            "match": {},
            "component_diff": ' [  \n   {  \n     "code": "Extension",  \n-    "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-coding-sctdescid"  \n     "profile": "https://fhir.nhs.uk/STU3/StructureDefinition/Extension-coding-sctdescid"  \n   }  \n ]  \n',
            "base": '```json\n[\n  {\n    "code": "Extension"\n  }\n]\n```',
        }
    },
    "AllergyIntolerance.reaction.manifestation.coding:snomedCT.system": {
        "fixedUri": {
            "table_result": (
                'Match. "fixedUri" == http://snomed.info/sct',
                'Match. "fixedUri" == http://snomed.info/sct',
            ),
            "match": {},
            "component_diff": {},
            "base": '"fixedUri" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.reaction.manifestation.coding:snomedCT.code": {
        "min": {
            "table_result": ('Match. "min" == 1', 'Match. "min" == 1'),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.reaction.severity": {
        "mustSupport": {
            "table_result": ("Not defined", True),
            "match": {},
            "component_diff": {},
            "base": '"mustSupport" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.reaction.exposureRoute": {
        "binding": {
            "table_result": ("See diff", "See diff"),
            "match": {},
            "component_diff": ' {  \n   "extension": [  \n     {  \n       "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-bindingName",  \n       "valueString": "RouteOfAdministration"  \n     }  \n   ],  \n   "strength": "example",  \n   "valueSetReference": {  \n-    "reference": "https://fhir.hl7.org.uk/STU3/ValueSet/CareConnect-AllergyExposureRoute-1"  \n     "reference": "https://fhir.nhs.uk/STU3/ValueSet/CareConnect-AllergyExposureRoute-1"  \n   }  \n }  \n',
            "base": '```json\n{\n  "description": "A coded concept describing the route or physiological path of administration of a therapeutic agent into or onto the body of a subject.",\n  "extension": [\n    {\n      "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-bindingName",\n      "valueString": "RouteOfAdministration"\n    }\n  ],\n  "strength": "example",\n  "valueSetReference": {\n    "reference": "http://hl7.org/fhir/ValueSet/route-codes"\n  }\n}\n```',
        }
    },
    "AllergyIntolerance.reaction.exposureRoute.coding": {
        "slicing": {
            "table_result": ("Match", "Match"),
            "match": '{\n  "discriminator": [\n    {\n      "path": "system",\n      "type": "value"\n    }\n  ],\n  "ordered": false,\n  "rules": "open"\n}',
            "component_diff": {},
            "base": '"slicing" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT": {
        "max": {
            "table_result": ('Match. "max" == 1', 'Match. "max" == 1'),
            "match": {},
            "component_diff": {},
            "base": '"max" == *',
        }
    },
    "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.extension": {
        "slicing": {
            "table_result": ("Match", "Match"),
            "match": '{\n  "discriminator": [\n    {\n      "path": "url",\n      "type": "value"\n    }\n  ],\n  "rules": "open"\n}',
            "component_diff": {},
            "base": '```json\n{\n  "description": "Extensions are always sliced by (at least) url",\n  "discriminator": [\n    {\n      "path": "url",\n      "type": "value"\n    }\n  ],\n  "rules": "open"\n}\n```',
        }
    },
    "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.extension:snomedCTDescriptionID": {
        "type": {
            "table_result": ("See diff", "See diff"),
            "match": {},
            "component_diff": ' [  \n   {  \n     "code": "Extension",  \n-    "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-coding-sctdescid"  \n     "profile": "https://fhir.nhs.uk/STU3/StructureDefinition/Extension-coding-sctdescid"  \n   }  \n ]  \n',
            "base": '```json\n[\n  {\n    "code": "Extension"\n  }\n]\n```',
        }
    },
    "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.system": {
        "fixedUri": {
            "table_result": (
                'Match. "fixedUri" == http://snomed.info/sct',
                'Match. "fixedUri" == http://snomed.info/sct',
            ),
            "match": {},
            "component_diff": {},
            "base": '"fixedUri" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.code": {
        "min": {
            "table_result": ('Match. "min" == 1', 'Match. "min" == 1'),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.reaction.note.author[x]": {
        "type": {
            "table_result": ("See diff", "See diff"),
            "match": {},
            "component_diff": ' [  \n   {  \n     "code": "Reference",  \n     "targetProfile": "http://hl7.org/fhir/StructureDefinition/RelatedPerson"  \n   },  \n   {  \n     "code": "string"  \n   },  \n   {  \n     "code": "Reference",  \n-    "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Patient-1"  \n     "targetProfile": "https://fhir.nhs.uk/STU3/StructureDefinition/CareConnect-GPC-Patient-1"  \n   },  \n   {  \n     "code": "Reference",  \n-    "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Practitioner-1"  \n     "targetProfile": "https://fhir.nhs.uk/STU3/StructureDefinition/CareConnect-GPC-Practitioner-1"  \n   }  \n ]  \n',
            "base": '```json\n[\n  {\n    "code": "Reference",\n    "targetProfile": "http://hl7.org/fhir/StructureDefinition/Practitioner"\n  },\n  {\n    "code": "Reference",\n    "targetProfile": "http://hl7.org/fhir/StructureDefinition/Patient"\n  },\n  {\n    "code": "Reference",\n    "targetProfile": "http://hl7.org/fhir/StructureDefinition/RelatedPerson"\n  },\n  {\n    "code": "string"\n  }\n]\n```',
        }
    },
    "AllergyIntolerance.identifier.assigner": {
        "type": {
            "table_result": ("Nothing to diff, value below", "Not defined"),
            "match": {},
            "component_diff": '[\n  {\n    "code": "Reference",\n    "targetProfile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/CareConnect-Organization-1"\n  }\n]',
            "base": '```json\n[\n  {\n    "code": "Reference",\n    "targetProfile": "http://hl7.org/fhir/StructureDefinition/Organization"\n  }\n]\n```',
        }
    },
    "AllergyIntolerance.code.coding": {
        "slicing": {
            "table_result": ("Nothing to diff, value below", "Not defined"),
            "match": {},
            "component_diff": '{\n  "discriminator": [\n    {\n      "path": "system",\n      "type": "value"\n    }\n  ],\n  "rules": "open"\n}',
            "base": '"slicing" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.code.coding:snomedCT": {
        "binding": {
            "table_result": ("Nothing to diff, value below", "Not defined"),
            "match": {},
            "component_diff": '{\n  "description": "A code from the SNOMED Clinical Terminology UK or a code from the v3 Code System NullFlavor specifying why a valid value is not present.",\n  "strength": "example",\n  "valueSetReference": {\n    "reference": "https://fhir.hl7.org.uk/STU3/ValueSet/CareConnect-AllergyCode-1"\n  }\n}',
            "base": '"binding" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.code.coding:snomedCT.extension": {
        "slicing": {
            "table_result": ("Nothing to diff, value below", "Not defined"),
            "match": {},
            "component_diff": '{\n  "discriminator": [\n    {\n      "path": "url",\n      "type": "value"\n    }\n  ],\n  "rules": "open"\n}',
            "base": '```json\n{\n  "description": "Extensions are always sliced by (at least) url",\n  "discriminator": [\n    {\n      "path": "url",\n      "type": "value"\n    }\n  ],\n  "rules": "open"\n}\n```',
        }
    },
    "AllergyIntolerance.code.coding:snomedCT.extension:snomedCTDescriptionID": {
        "type": {
            "table_result": ("Nothing to diff, value below", "Not defined"),
            "match": {},
            "component_diff": '[\n  {\n    "code": "Extension",\n    "profile": "https://fhir.hl7.org.uk/STU3/StructureDefinition/Extension-coding-sctdescid"\n  }\n]',
            "base": '```json\n[\n  {\n    "code": "Extension"\n  }\n]\n```',
        }
    },
    "AllergyIntolerance.code.coding:snomedCT.system": {
        "min": {
            "table_result": (1, "Not defined"),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.code.coding:snomedCT.code": {
        "min": {
            "table_result": (1, "Not defined"),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.code.coding:snomedCT.display": {
        "min": {
            "table_result": (1, "Not defined"),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.reaction.substance.coding:snomedCT.display": {
        "min": {
            "table_result": (1, "Not defined"),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.reaction.manifestation.coding:snomedCT.display": {
        "min": {
            "table_result": (1, "Not defined"),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.display": {
        "min": {
            "table_result": (1, "Not defined"),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.meta.profile": {
        "min": {
            "table_result": ("Not defined", 1),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.identifier": {
        "min": {
            "table_result": ("Not defined", 1),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.clinicalStatus": {
        "min": {
            "table_result": ("Not defined", 1),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.category": {
        "min": {
            "table_result": ("Not defined", 1),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.code": {
        "binding": {
            "table_result": ("Not defined", "Nothing to diff, value below"),
            "match": {},
            "component_diff": '{\n  "extension": [\n    {\n      "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-bindingName",\n      "valueString": "AllergyIntoleranceCode"\n    }\n  ],\n  "strength": "example",\n  "valueSetReference": {\n    "reference": "https://fhir.nhs.uk/STU3/ValueSet/CareConnect-AllergyCode-1"\n  }\n}',
            "base": '```json\n{\n  "description": "Type of the substance/product, allergy or intolerance condition, or negation/exclusion codes for reporting no known allergies.",\n  "extension": [\n    {\n      "url": "http://hl7.org/fhir/StructureDefinition/elementdefinition-bindingName",\n      "valueString": "AllergyIntoleranceCode"\n    }\n  ],\n  "strength": "example",\n  "valueSetReference": {\n    "reference": "http://hl7.org/fhir/ValueSet/allergyintolerance-code"\n  }\n}\n```',
        }
    },
    "AllergyIntolerance.code.coding.extension": {
        "slicing": {
            "table_result": ("Not defined", "Nothing to diff, value below"),
            "match": {},
            "component_diff": '{\n  "discriminator": [\n    {\n      "path": "url",\n      "type": "value"\n    }\n  ],\n  "rules": "open"\n}',
            "base": '```json\n{\n  "description": "Extensions are always sliced by (at least) url",\n  "discriminator": [\n    {\n      "path": "url",\n      "type": "value"\n    }\n  ],\n  "rules": "open"\n}\n```',
        }
    },
    "AllergyIntolerance.code.coding.extension:snomedCTDescriptionID": {
        "type": {
            "table_result": ("Not defined", "Nothing to diff, value below"),
            "match": {},
            "component_diff": '[\n  {\n    "code": "Extension",\n    "profile": "https://fhir.nhs.uk/STU3/StructureDefinition/Extension-coding-sctdescid"\n  }\n]',
            "base": '```json\n[\n  {\n    "code": "Extension"\n  }\n]\n```',
        }
    },
    "AllergyIntolerance.code.coding.system": {
        "min": {
            "table_result": ("Not defined", 1),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.code.coding.version": {
        "max": {
            "table_result": ("Not defined", "0"),
            "match": {},
            "component_diff": {},
            "base": '"max" == 1',
        }
    },
    "AllergyIntolerance.code.coding.code": {
        "min": {
            "table_result": ("Not defined", 1),
            "match": {},
            "component_diff": {},
            "base": '"min" == 0',
        }
    },
    "AllergyIntolerance.note": {
        "mustSupport": {
            "table_result": ("Not defined", True),
            "match": {},
            "component_diff": {},
            "base": '"mustSupport" is not defined in the base element definition.',
        }
    },
    "AllergyIntolerance.reaction.substance.coding:snomedCT.version": {
        "max": {
            "table_result": ("Not defined", "0"),
            "match": {},
            "component_diff": {},
            "base": '"max" == 1',
        }
    },
    "AllergyIntolerance.reaction.manifestation.coding:snomedCT.version": {
        "max": {
            "table_result": ("Not defined", "0"),
            "match": {},
            "component_diff": {},
            "base": '"max" == 1',
        }
    },
    "AllergyIntolerance.reaction.exposureRoute.coding:snomedCT.version": {
        "max": {
            "table_result": ("Not defined", "0"),
            "match": {},
            "component_diff": {},
            "base": '"max" == 1',
        }
    },
}

x = {
    "AllergyIntolerance.extension": (
        {
            "id": "AllergyIntolerance.extension",
            "path": "AllergyIntolerance.extension",
            "slicing": {
                "discriminator": [{"type": "value", "path": "url"}],
                "rules": "open",
            },
            "base": {"path": "DomainResource.extension", "min": 0, "max": "*"},
        },
        {
            "id": "AllergyIntolerance.extension",
            "path": "AllergyIntolerance.extension",
            "slicing": {
                "discriminator": [{"type": "value", "path": "url"}],
                "rules": "open",
            },
            "base": {"path": "DomainResource.extension", "min": 0, "max": "*"},
        },
    )
}
