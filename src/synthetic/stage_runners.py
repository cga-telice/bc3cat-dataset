"""In-memory pure stage runners for the BC3 pipeline (Sprint 17 — Task D1).

The s03/s04/s05/s07 pipeline stages are notebooks whose core transforms are
factored into functions wrapped in file-IO / chunked-streaming drivers. This
module relocates those core transforms verbatim into importable, pure
dict -> dict functions so the pipeline can be rerun in process on a mutated
in-memory stage JSON (the Stage-B rerun, Sprint 18).

Contract:
  run_stage3(stage2) -> stage3   Cartesian parametric expansion (s03).
  run_stage4(stage3) -> stage4   Text-variable formula resolution (s04).
  run_stage5(stage4) -> stage5   Template instantiation + field filter (s05).
  run_stage7(stage5) -> stage7   In-memory dedup, first-wins (s07).
  run_stages_3_to_7(stage2) -> stage7   Chains the four (s06 skipped).

Each runner is pure: it deep-copies its input, never mutates it, performs no
disk IO, and has no module-level side effects. The runners are mutation-blind
pure pipeline transforms — they import only stdlib and src/utils, never the
synthetic mutation stack (mutator / taxonomy / run_synthetic / layer_* /
composition / variant_* / rule_emitter / slot_extractor). Rule injection
between stages is the orchestrator's job (Sprint 18).
"""
import copy
import re
from collections import defaultdict
from itertools import product
from math import (  # noqa: F401 -- names referenced by eval'd formulas
    sin, cos, tan, asin, acos, atan, atan2, sqrt, fabs as ABS, floor as INT,
)

from utils.z_formula_processing import translate_formula_to_python, quote_second_term  # noqa: F401

__all__ = [
    "run_stage3",
    "run_stage4",
    "run_stage5",
    "run_stage7",
    "run_stages_3_to_7",
]


# ---------------------------------------------------------------------------
# Stage 3 — Cartesian parametric expansion (relocated from s03 verbatim)
# ---------------------------------------------------------------------------

def generate_combinations(parameters):
    """Generate all combinations of parameter values."""
    keys = list(parameters.keys())  # List of parameter keys
    values = [
        [
            {
                "label": value["label"],
                "value": value["value"]
            } for value in parameters[key]["values"]
        ] for key in keys
    ]
    combinations = product(*values)  # Cartesian product of all values
    return keys, combinations


def transform_data(data):
    """Transform the data by generating all parameter combinations."""
    transformed_data = {}

    for parent_key, content in data.items():
        if "parameters" not in content:
            # Add items without parameters
            item_key = f"{parent_key}"  # Generate unique key
            transformed_data[item_key] = {
                "parent_key": parent_key,
                "ud": content["ud"],
                "concept": content["concept"],
                "text_variables": {},
                "resumen": content["concept"],
                "texto": content["concept"],
                "parameters": {}
            }

        else:
            parameters = content["parameters"]
            keys, combinations = generate_combinations(parameters)

            for combination in combinations:
                key_suffix = "".join([param["label"] for param in combination])
                item_key = f"{parent_key[:-1]}{key_suffix}"  # Generate unique key for each combination

                # Construct the parameters with only the selected values
                new_parameters = {
                    key: {
                        "label": parameters[key]["label"],
                        "values": [
                            combination[i]
                        ]
                    } for i, key in enumerate(keys)
                }

                # Add transformed item to the result
                transformed_data[item_key] = {
                    "parent_key": parent_key,
                    "ud": content["ud"],
                    "concept": content["concept"],
                    "text_variables": content["text_variables"],
                    "resumen": content["resumen"],
                    "texto": content["texto"],
                    "parameters": new_parameters
                }

    return transformed_data


def run_stage3(stage2_json: dict) -> dict:
    """Cartesian parametric expansion (s03 core, in memory, pure)."""
    return transform_data(copy.deepcopy(stage2_json))


# ---------------------------------------------------------------------------
# Stage 4 — text-variable formula resolution (relocated from s04 verbatim)
#
# NOTE (Sprint 17 reconciliation): s04 carried an *inline* copy of
# translate_formula_to_python / quote_second_term that had DRIFTED from the
# canonical utils.z_formula_processing exports (the inline copy dropped the
# "=" -> "==" mapping, added \b word boundaries, and never called
# quote_second_term). To reproduce the committed golden stage4 byte-for-byte
# this module imports and uses the *inline notebook* behaviour, preserved here
# as `_translate_formula_to_python_s04`. See docs/synthetic/RESEARCH_LOG.md
# (Sprint 17) for the full diff and the decision rationale.
# ---------------------------------------------------------------------------

def _translate_formula_to_python_s04(formula):
    """Translate formula string into Python syntax (s04 notebook variant).

    Verbatim relocation of s04's inline translate. Differs from the canonical
    `utils.z_formula_processing.translate_formula_to_python`: no "=" -> "=="
    entry, word-boundary-anchored operator substitution, and no trailing
    `quote_second_term` call. Required for golden byte-equivalence.
    """
    python_equivalents = {
        "@": " or ",
        "&": " and ",
        "^": "**",
        "<>": "!=",
        "ABS": "ABS",
        "INT": "INT",
        "ROUND": "round",
        "SIN": "sin",
        "COS": "cos",
        "TAN": "tan",
        "ASIN": "asin",
        "ACOS": "acos",
        "ATAN": "atan",
        "ATAN2": "atan2",
        "SQRT": "sqrt",
        "ATOF": "float",
        "FTOA": "str",
    }

    for custom, py_equiv in python_equivalents.items():
        formula = re.sub(r'\b' + re.escape(custom) + r'\b', py_equiv, formula)

    formula = re.sub(r'\(%(\w)=(\w)\)', r'(1 if \1=="\2" else 0)', formula)

    return formula


def is_already_quoted(text):
    return bool(re.match(r'^".*"$', text.strip()))


def safe_quote(text):
    if is_already_quoted(text):
        return text
    return f'"{text}"'


def is_formula(text):
    if not isinstance(text, str):
        return False
    formula_indicators = ['+', '-', '*', '/', '=', '<>', '@', '&', '^',
                          'ABS', 'INT', 'ROUND', 'SIN', 'COS', 'TAN',
                          'ASIN', 'ACOS', 'ATAN', 'ATAN2', 'SQRT', 'ATOF', 'FTOA',
                          '==']
    return any(indicator in text for indicator in formula_indicators)


def is_comparison_placeholder(text, placeholder_type, key):
    pattern = rf'[{placeholder_type}]{key}\s*==|==\s*[{placeholder_type}]{key}'
    return bool(re.search(pattern, text))


def find_text_variable_references(text):
    if not isinstance(text, str):
        return []
    pattern = r'\$([A-Za-z0-9]+)(?:\(.*?\))?'
    return re.findall(pattern, text)


def find_parameter_placeholders(text):
    if not isinstance(text, str):
        return []
    text_var_pattern = r'\$([A-Za-z0-9]+)(?:\(.*?\))'
    temp_text = re.sub(text_var_pattern, '', text)
    return re.findall(r'[%$]([A-Za-z0-9]+)', temp_text)


def replace_parameter_placeholder(text, parameters, placeholder_type, key, is_formula_var=False):
    try:
        if not parameters.get(key):
            return text

        param_value = parameters[key]['values'][0]
        is_comparison = is_formula_var and is_comparison_placeholder(text, placeholder_type, key)
        replacement = param_value['label'] if is_comparison else param_value['value']

        if is_formula_var and not is_already_quoted(replacement):
            replacement = safe_quote(replacement)

        pattern = f'[{placeholder_type}]{key}\\b'
        return re.sub(pattern, replacement, text)
    except Exception as e:
        debug_print("replace_parameter_placeholder", text, e)
        return text


def resolve_text_variable_reference(reference, text_vars):
    try:
        match = re.match(r'\$(\w+)(?:\((.*?)\))?', reference)
        if not match:
            return reference

        var_name, args = match.groups()
        if var_name not in text_vars:
            return reference

        referenced_var = text_vars[var_name]
        resolved_value = referenced_var.get('evaluated', '')

        if isinstance(resolved_value, str):
            if not is_already_quoted(resolved_value):
                return safe_quote(resolved_value)
            return resolved_value

        if args and isinstance(resolved_value, list):
            arg_list = [arg.strip() for arg in args.split(',')]
            result = resolved_value
            for arg in arg_list:
                if isinstance(result, list):
                    try:
                        index = int(arg) if arg.isdigit() else 0
                        result = result[index]
                    except (IndexError, ValueError):
                        return reference
            if isinstance(result, str) and not is_already_quoted(result):
                return safe_quote(result)
            return result

        return reference
    except Exception:
        return reference


def evaluate_formula(formula_text):
    try:
        clean_formula = re.sub(r'"\s*"', '" "', formula_text)
        python_formula = _translate_formula_to_python_s04(clean_formula)
        result = eval(python_formula)
        return result
    except Exception as e:
        debug_print("evaluate_formula", formula_text, e)
        return formula_text


def debug_print(context, value, error=None):
    """No-op debug hook (silent, as in the s04 notebook)."""
    if error:
        pass


def process_single_item(text, parameters, is_formula_var):
    """Process a single text item."""
    try:
        if not isinstance(text, str):
            return {
                'original': text,
                'replaced': text,
                'evaluated': text,
                'dependencies': []
            }

        dependencies = find_text_variable_references(text)
        if dependencies:
            return {
                'original': text,
                'replaced': text,
                'evaluated': text,
                'dependencies': dependencies
            }

        replaced_text = text
        placeholders = find_parameter_placeholders(text)

        for placeholder in placeholders:
            use_label = is_formula_var
            for prefix in ['%', '$']:
                new_text = replace_parameter_placeholder(
                    replaced_text, parameters, prefix, placeholder, use_label
                )
                replaced_text = new_text

        evaluated_text = evaluate_formula(replaced_text) if is_formula_var else replaced_text

        return {
            'original': text,
            'replaced': replaced_text,
            'evaluated': evaluated_text,
            'dependencies': []
        }
    except Exception as e:
        debug_print("process_single_item", text, e)
        return {
            'original': text,
            'replaced': text,
            'evaluated': text,
            'dependencies': []
        }


def process_text_variables(data):
    """First pass: process text variables with direct parameter replacements."""
    try:
        for key, item in data.items():
            if 'text_variables' not in item or 'parameters' not in item:
                continue

            text_vars = item['text_variables']
            parameters = item['parameters']
            processed_vars = {}

            for var_key, var_value in text_vars.items():
                try:
                    is_formula_var = is_formula(str(var_value))

                    if isinstance(var_value, str):
                        processed = process_single_item(var_value, parameters, is_formula_var)
                        processed_vars[var_key] = {
                            'original': processed['original'],
                            'replaced': processed['replaced'],
                            'evaluated': processed['evaluated'],
                            'is_formula': is_formula_var,
                            'dependencies': processed['dependencies'],
                            'fully_processed': not processed['dependencies'] and
                                            not bool(find_parameter_placeholders(processed['replaced']))
                        }
                    elif isinstance(var_value, list):
                        processed_list = []
                        all_dependencies = set()

                        for list_item in var_value:
                            if isinstance(list_item, list):
                                nested_processed = [
                                    process_single_item(x, parameters, is_formula_var)
                                    for x in list_item
                                ]
                                processed_list.append(nested_processed)
                                for x in nested_processed:
                                    all_dependencies.update(x['dependencies'])
                            else:
                                item_processed = process_single_item(list_item, parameters, is_formula_var)
                                processed_list.append(item_processed)
                                all_dependencies.update(item_processed['dependencies'])

                        processed_vars[var_key] = {
                            'original': var_value,
                            'replaced': [
                                [x['replaced'] for x in item] if isinstance(item, list)
                                else item['replaced'] for item in processed_list
                            ],
                            'evaluated': [
                                [x['evaluated'] for x in item] if isinstance(item, list)
                                else item['evaluated'] for item in processed_list
                            ],
                            'is_formula': is_formula_var,
                            'dependencies': list(all_dependencies),
                            'fully_processed': not all_dependencies and
                                            not any(find_parameter_placeholders(str(x['replaced']))
                                                for item in processed_list
                                                for x in (item if isinstance(item, list) else [item]))
                        }
                except Exception as e:
                    debug_print(f"Processing var {var_key}", var_value, e)
                    processed_vars[var_key] = {
                        'original': var_value,
                        'replaced': var_value,
                        'evaluated': var_value,
                        'is_formula': False,
                        'dependencies': [],
                        'fully_processed': False,
                        'error': str(e)
                    }

            item['text_variables'] = processed_vars

        return data
    except Exception as e:
        debug_print("process_text_variables", "main process", e)
        raise


def process_unresolved_variables(data):
    """Second pass: process variables that depend on other text variables."""
    for key, item in data.items():
        if 'text_variables' not in item:
            continue

        text_vars = item['text_variables']
        parameters = item.get('parameters', {})

        unprocessed_vars = {
            var_key: var_data
            for var_key, var_data in text_vars.items()
            if not var_data.get('fully_processed', False)
        }

        for var_key, var_data in unprocessed_vars.items():
            try:
                original = var_data['original']
                is_formula_var = var_data['is_formula']
                replaced_text = original

                references = find_text_variable_references(original)
                for ref in references:
                    ref_pattern = rf'\${ref}(?:\([^)]*\))?'
                    matches = list(re.finditer(ref_pattern, replaced_text))

                    for match in reversed(matches):
                        full_ref = match.group(0)
                        resolved_value = resolve_text_variable_reference(full_ref, text_vars)
                        replaced_text = replaced_text[:match.start()] + str(resolved_value) + replaced_text[match.end():]

                placeholders = find_parameter_placeholders(replaced_text)
                for placeholder in placeholders:
                    for prefix in ['%', '$']:
                        replaced_text = replace_parameter_placeholder(
                            replaced_text, parameters, prefix, placeholder,
                            is_formula_var=is_formula_var
                        )

                replaced_text = re.sub(r'\s+', ' ', replaced_text)

                text_vars[var_key].update({
                    'replaced': replaced_text,
                    'evaluated': evaluate_formula(replaced_text) if is_formula_var else replaced_text,
                    'fully_processed': True
                })

            except Exception as e:
                debug_print(f"Error processing {var_key}", str(e))
                text_vars[var_key].update({
                    'error': str(e),
                    'fully_processed': False
                })

    return data


def run_stage4(stage3_json: dict) -> dict:
    """Text-variable formula resolution (s04 core, in memory, pure)."""
    data = copy.deepcopy(stage3_json)
    return process_unresolved_variables(process_text_variables(data))


# ---------------------------------------------------------------------------
# Stage 5 — template instantiation + field filter (relocated from s05 verbatim)
# ---------------------------------------------------------------------------

def get_variable_value(var_name, function_params, text_vars, params):
    """Get value for a variable or function from text_variables or parameters."""
    if function_params:
        if var_name in text_vars:
            indices = []
            for param in function_params.split(','):
                param = param.strip()
                if param.startswith('%'):
                    param_key = param[1:]
                    if param_key in params and params[param_key]['values']:
                        label = params[param_key]['values'][0]['label']
                        if label.isalpha():
                            indices.append(ord(label.lower()) - ord('a'))
                        else:
                            indices.append(0)
                    else:
                        indices.append(0)
                elif param.isalpha():
                    indices.append(ord(param.lower()) - ord('a'))
                else:
                    try:
                        indices.append(int(param))
                    except ValueError:
                        indices.append(0)

            result = text_vars[var_name]['evaluated']
            for idx in indices:
                if isinstance(result, list) and idx < len(result):
                    result = result[idx]
            return str(result).strip('"')

        return ''

    if var_name in params:
        return str(params[var_name]['values'][0]['value'])
    elif var_name in text_vars:
        result = text_vars[var_name]['evaluated']
        if isinstance(result, list):
            result = result[0]
        return str(result).strip('"')

    return ''


def evaluate_string(text, text_vars, params):
    """Evaluate a string by replacing all placeholders with their values."""
    result = text

    pattern = r'\$([A-Z])\((.*?)\)'
    matches = list(re.finditer(pattern, result))
    for match in reversed(matches):
        var_name = match.group(1)
        function_params = match.group(2)
        replacement = get_variable_value(var_name, function_params, text_vars, params)
        result = result[:match.start()] + replacement + result[match.end():]

    pattern = r'\$([A-Z])'
    matches = list(re.finditer(pattern, result))
    for match in reversed(matches):
        var_name = match.group(1)
        replacement = get_variable_value(var_name, '', text_vars, params)
        result = result[:match.start()] + replacement + result[match.end():]

    result = result.replace('\\', '')

    return result.strip()


def process_json(input_data):
    """Process the input JSON and evaluate resumen and texto fields."""
    for key, item in input_data.items():
        if isinstance(item, dict):
            if 'resumen' in item and 'texto' in item:
                text_vars = item.get('text_variables', {})
                params = item.get('parameters', {})

                item['resumen'] = evaluate_string(item['resumen'], text_vars, params)
                item['texto'] = evaluate_string(item['texto'], text_vars, params)

    return input_data


def filter_fields(data):
    """Keep only specified fields in the JSON."""
    filtered_data = {}
    fields_to_keep = ['parent_key', 'ud', 'concept', 'resumen', 'texto', 'parameters']

    for key, item in data.items():
        if isinstance(item, dict):
            filtered_item = {field: item[field] for field in fields_to_keep if field in item}
            filtered_data[key] = filtered_item

    return filtered_data


def run_stage5(stage4_json: dict) -> dict:
    """Template instantiation + field filter (s05 core, in memory, pure)."""
    data = copy.deepcopy(stage4_json)
    return filter_fields(process_json(data))


# ---------------------------------------------------------------------------
# Stage 7 — in-memory dedup (s07 marcar_duplicados + filter_json, fused, pure)
# ---------------------------------------------------------------------------

def _mark_duplicates(data):
    """In-memory equivalent of s07.marcar_duplicados (adds `validation` flag)."""
    resumen_map = defaultdict(list)
    texto_map = defaultdict(list)

    for key, item in data.items():
        resumen = item.get("resumen", "").strip()
        texto = item.get("texto", "").strip()
        resumen_map[resumen].append(key)
        texto_map[texto].append(key)

    duplicados = set()
    for mapa in (resumen_map, texto_map):
        for lista in mapa.values():
            if len(lista) > 1:
                duplicados.update(lista)

    for key in data:
        data[key]["validation"] = key not in duplicados

    return data


def _filter_json(json_data):
    """In-memory equivalent of s07.filter_json (validated + first-wins unique)."""
    result = {}
    seen_resumens = set()
    seen_textos = set()

    for key, item in json_data.items():
        if item.get('validation') == True:  # noqa: E712 -- verbatim from s07
            resumen = item.get('resumen')
            texto = item.get('texto')

            if resumen not in seen_resumens and texto not in seen_textos:
                seen_resumens.add(resumen)
                seen_textos.add(texto)

                result[key] = item

    return result


def run_stage7(stage5_json: dict) -> dict:
    """In-memory dedup: mark duplicates then filter (s07 core, pure, no IO)."""
    data = copy.deepcopy(stage5_json)
    return _filter_json(_mark_duplicates(data))


# ---------------------------------------------------------------------------
# Convenience chain — s03 -> s04 -> s05 -> s07 (s06 skipped; no rule injection)
# ---------------------------------------------------------------------------

def run_stages_3_to_7(stage2_json: dict) -> dict:
    """Chain run_stage3 -> run_stage4 -> run_stage5 -> run_stage7 (s06 skipped).

    No rule injection — that is Sprint 18's orchestrator concern. This is the
    function Sprint 18 will interleave `mutator.apply_*` calls between.
    """
    return run_stage7(run_stage5(run_stage4(run_stage3(stage2_json))))
