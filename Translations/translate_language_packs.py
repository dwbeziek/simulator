import json
import time
import re
from googletrans import Translator

# ICU pattern for pluralization and placeholders
ICU_PLACEHOLDER_PATTERN = re.compile(r"{\\s*[\\w\\.\\#\\,\\s='\\\"|\\(\\)-]+}")

# Load the English source file
with open('locale.constant-en_US.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Flatten nested JSON
def flatten_json(y, prefix=''):
    flat = {}
    for k, v in y.items():
        if isinstance(v, dict):
            flat.update(flatten_json(v, f"{prefix}{k}."))
        else:
            flat[prefix + k] = v
    return flat

# Unflatten back to nested JSON
def unflatten_json(flat_dict):
    nested = {}
    for compound_key, value in flat_dict.items():
        keys = compound_key.split('.')
        d = nested
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value
    return nested

# Translate the flattened JSON
def translate_flat_json(flat_dict, target_lang):
    translator = Translator()
    translated = {}
    for key, text in flat_dict.items():
        success = False
        for attempt in range(1):
            try:
                if not isinstance(text, str) or text.strip() == "":
                    print(f"Skipping key {key}: Not a valid string ({text})")
                    translated[key] = text
                    break
                if ICU_PLACEHOLDER_PATTERN.search(text) or '{{' in text or '}}' in text:
                    print(f"Skipping key {key}: Contains ICU or placeholders → {text}")
                    translated[key] = text
                    break

                time.sleep(0.2)
                translated_text = translator.translate(text, src='en', dest=target_lang).text

                if not isinstance(translated_text, str):
                    raise ValueError("Translated text is not a string")

                translated[key] = translated_text
                success = True
                break

            except Exception as e:
                print(f"Attempt {attempt+1} failed for {key}: {e} | Value: {text}")
                time.sleep(0.5)

        if not success:
            print(f"Translation ultimately failed for {key}: keeping original.")
            translated[key] = text
    return translated

# Start processing
flat_data = flatten_json(data)

# Translate to Swedish and Finnish
translated_sv = translate_flat_json(flat_data, 'sv')
translated_fi = translate_flat_json(flat_data, 'fi')

# Unflatten and save to files
with open('locale.constant-sv_SE.json', 'w', encoding='utf-8') as f:
    json.dump(unflatten_json(translated_sv), f, indent=2, ensure_ascii=False)

with open('locale.constant-fi_FI.json', 'w', encoding='utf-8') as f:
    json.dump(unflatten_json(translated_fi), f, indent=2, ensure_ascii=False)

print("✅ Translation completed. Files saved as locale.constant-sv_SE.json and locale.constant-fi_FI.json")
