"""Small JSON Schema (2020-12) validator, stdlib only, covering the keywords used by
the AARS contract schema: type, enum, const, required, properties, additionalProperties,
items, minItems, maxItems, minProperties, minLength, maxLength, pattern, minimum, maximum,
exclusiveMinimum, exclusiveMaximum, $ref (local), oneOf.

Unknown keywords make it raise, so a newer schema cannot be validated silently wrong.
Integers must be JSON integers (606800, not 606800.0): stricter than jsonschema on purpose."""
import json
import re

KNOWN = {"$schema", "$id", "$defs", "title", "description", "discriminator", "type", "enum", "const",
         "required", "properties", "additionalProperties", "items", "minItems", "maxItems",
         "minProperties", "minLength", "maxLength", "pattern", "minimum", "maximum",
         "exclusiveMinimum", "exclusiveMaximum", "$ref", "oneOf"}


def _is_type(v, t):
    if t == "object":
        return isinstance(v, dict)
    if t == "array":
        return isinstance(v, list)
    if t == "string":
        return isinstance(v, str)
    if t == "boolean":
        return isinstance(v, bool)
    if t == "null":
        return v is None
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    raise ValueError("unsupported type " + t)


class Validator:
    def __init__(self, schema):
        self.root = schema

    def _resolve(self, ref):
        if not ref.startswith("#/"):
            raise ValueError("only local $ref supported: " + ref)
        node = self.root
        for part in ref[2:].split("/"):
            node = node[part]
        return node

    def errors(self, value, schema=None, path="$"):
        schema = self.root if schema is None else schema
        unknown = set(schema) - KNOWN
        if unknown:
            raise ValueError("unsupported schema keywords %s at %s" % (sorted(unknown), path))
        errs = []
        if "$ref" in schema:
            errs += self.errors(value, self._resolve(schema["$ref"]), path)
        if "type" in schema:
            types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            if not any(_is_type(value, t) for t in types):
                return errs + ["%s: expected %s, got %r" % (path, "/".join(types), value)]
        if "const" in schema and value != schema["const"]:
            errs.append("%s: must be %r" % (path, schema["const"]))
        if "enum" in schema and value not in schema["enum"]:
            errs.append("%s: %r not in %s" % (path, value, schema["enum"]))
        if "oneOf" in schema:
            ok = [i for i, s in enumerate(schema["oneOf"]) if not self.errors(value, s, path)]
            if len(ok) != 1:
                # report the errors of the branch whose const 'type' matches, if any (readable messages)
                detail = ""
                if isinstance(value, dict) and "type" in value:
                    for s in schema["oneOf"]:
                        target = self._resolve(s["$ref"]) if "$ref" in s else s
                        if target.get("properties", {}).get("type", {}).get("const") == value["type"]:
                            detail = "; ".join(self.errors(value, s, path))
                errs.append("%s: matches %d of oneOf%s" % (path, len(ok), (" (" + detail + ")") if detail else ""))
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                errs.append("%s: %r < minimum %r" % (path, value, schema["minimum"]))
            if "maximum" in schema and value > schema["maximum"]:
                errs.append("%s: %r > maximum %r" % (path, value, schema["maximum"]))
            if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
                errs.append("%s: %r <= exclusiveMinimum %r" % (path, value, schema["exclusiveMinimum"]))
            if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
                errs.append("%s: %r >= exclusiveMaximum %r" % (path, value, schema["exclusiveMaximum"]))
        if isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                errs.append("%s: shorter than %d" % (path, schema["minLength"]))
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                errs.append("%s: longer than %d" % (path, schema["maxLength"]))
            if "pattern" in schema and not re.search(schema["pattern"], value):
                errs.append("%s: %r does not match %s" % (path, value, schema["pattern"]))
        if isinstance(value, dict):
            for k in schema.get("required", []):
                if k not in value:
                    errs.append("%s: missing %s" % (path, k))
            if "minProperties" in schema and len(value) < schema["minProperties"]:
                errs.append("%s: fewer than %d properties" % (path, schema["minProperties"]))
            props = schema.get("properties", {})
            for k, v in value.items():
                if k in props:
                    errs += self.errors(v, props[k], "%s.%s" % (path, k))
                elif schema.get("additionalProperties") is False:
                    errs.append("%s: unknown field %s" % (path, k))
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                errs.append("%s: fewer than %d items" % (path, schema["minItems"]))
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                errs.append("%s: more than %d items" % (path, schema["maxItems"]))
            if "items" in schema:
                for i, v in enumerate(value):
                    errs += self.errors(v, schema["items"], "%s[%d]" % (path, i))
        return errs


def load(path):
    with open(path, encoding="utf-8") as f:
        return Validator(json.load(f))
