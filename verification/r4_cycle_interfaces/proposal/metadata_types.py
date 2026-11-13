"""Strict JSON provenance types, per ARB-R1-CI-SEMANTICS-02.

No coercion; this contract does not change physical arithmetic or the expression
normalizer. basis_revision remains the existing textual identity tag.
"""
import math


class MetadataTypeError(ValueError):
    kind = 'INPUT_ERROR'
    def __init__(self, path, expected):
        super().__init__('semantic:type:' + path + ':expected_' + expected)


def revision(value, lower=1):
    """Source/norm revisions >=1; fault/context/origin counters >=0."""
    return type(value) is int and value >= lower


def revision_map(value):
    return (type(value) is dict and all(type(k) is str and k and revision(v, 0)
                                       for k, v in value.items()))


def validate_metadata(value, path='$'):
    """Walk all nested source/ref/AST/binding/provenance objects before equality.

    Plural revision *snapshots* are checked with revision_map at their consumers:
    in documentary schemas origin_revisions can instead be a binding declaration
    or explanatory text. Those declarations are compared to the anchored norm.
    """
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str: raise MetadataTypeError(path, 'string_object_key')
            here = path + '/' + key
            if key in {'revision', 'increment', 'acceptance_PR'} and not revision(item):
                raise MetadataTypeError(here, 'integer_ge_1')
            if key in {'origin_revision', 'interface_consecutive_rejections', 'material_contract_consecutive_rejections', 'consecutive_rejections'} and not revision(item, 0):
                raise MetadataTypeError(here, 'integer_ge_0')
            if key == 'schema' and not (revision(item) or (type(item) is str and item)):
                raise MetadataTypeError(here, 'integer_schema_or_named_schema')
            validate_metadata(item, here)
    elif type(value) is list:
        for i, item in enumerate(value): validate_metadata(item, path + '/' + str(i))


def metadata_equal(left, right):
    """Exact JSON metadata type, shape and value, including nested booleans."""
    if type(left) is not type(right): return False
    if type(left) is dict:
        return (all(type(k) is str for k in left) and all(type(k) is str for k in right)
                and left.keys() == right.keys()
                and all(metadata_equal(left[k], right[k]) for k in left))
    if type(left) is list:
        return len(left) == len(right) and all(metadata_equal(a,b) for a,b in zip(left,right))
    if type(left) is float: return math.isfinite(left) and math.isfinite(right) and left == right
    return type(left) in {str, int, bool, type(None)} and left == right


def quantity_equal(left, right):
    """Keep permitted physical numeric equality; bool is never a quantity.

    Existing exact rational strings remain exact strings; no new parsing or
    float conversion is introduced here.
    """
    if type(left) is bool or type(right) is bool: return False
    if type(left) in {int, float} and type(right) in {int, float}:
        return math.isfinite(left) and math.isfinite(right) and left == right
    return metadata_equal(left, right)


def reference_equal(left, right):
    """Strict provenance plus existing quantity semantics for source-row value."""
    if type(left) is not dict or type(right) is not dict or left.keys() != right.keys(): return False
    return all((quantity_equal if k == 'value' else metadata_equal)(left[k], right[k]) for k in left)
